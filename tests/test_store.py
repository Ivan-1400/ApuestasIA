import os
import sqlite3
import tempfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.data import store


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    store.Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    db_session = session_factory()
    yield db_session
    db_session.close()


def test_save_prediction_once_does_not_duplicate(session):
    first = store.Prediction(
        fixture_id="mlb:123",
        sport="mlb",
        match_label="Away @ Home",
        outcome_label="Home",
        market="home_win",
        probability=0.6,
    )
    store.save_prediction_once(session, first)

    second = store.Prediction(
        fixture_id="mlb:123",
        sport="mlb",
        match_label="Away @ Home",
        outcome_label="Away",
        market="away_win",
        probability=0.4,
    )
    store.save_prediction_once(session, second)

    rows = session.query(store.Prediction).filter_by(fixture_id="mlb:123").all()
    assert len(rows) == 1
    assert rows[0].outcome_label == "Home"  # se queda con la primera pick, no la pisa


def test_save_prediction_once_allows_different_fixtures(session):
    store.save_prediction_once(
        session,
        store.Prediction(
            fixture_id="mlb:1", sport="mlb", match_label="A @ B", outcome_label="B",
            market="home_win", probability=0.6,
        ),
    )
    store.save_prediction_once(
        session,
        store.Prediction(
            fixture_id="mlb:2", sport="mlb", match_label="C @ D", outcome_label="D",
            market="home_win", probability=0.55,
        ),
    )
    assert session.query(store.Prediction).count() == 2


def test_resolve_writable_db_path_returns_original_when_writable(tmp_path):
    db_path = tmp_path / "apuestas.sqlite"
    assert store._resolve_writable_db_path(str(db_path)) == str(db_path)


def test_resolve_writable_db_path_falls_back_on_sqlite_operational_error(tmp_path, monkeypatch):
    """No depende de permisos reales del SO — en Windows, marcar un archivo de solo lectura
    con os.chmod no siempre bloquea la escritura para el dueño del archivo, así que un test
    basado en permisos del filesystem no es confiable multiplataforma. En cambio, simula
    directamente el error real que tira SQLite en Streamlit Cloud
    (`sqlite3.OperationalError: attempt to write a readonly database`)."""
    db_path = tmp_path / "apuestas.sqlite"
    db_path.write_bytes(b"contenido de prueba")

    real_connect = sqlite3.connect

    def fake_connect(path, *args, **kwargs):
        if os.path.abspath(str(path)) == os.path.abspath(str(db_path)):
            raise sqlite3.OperationalError("attempt to write a readonly database")
        return real_connect(path, *args, **kwargs)

    monkeypatch.setattr(store.sqlite3, "connect", fake_connect)

    fallback_path = os.path.join(tempfile.gettempdir(), "apuestasia_apuestas.sqlite")
    if os.path.exists(fallback_path):
        os.remove(fallback_path)

    result = store._resolve_writable_db_path(str(db_path))

    assert result == fallback_path
    assert os.path.exists(fallback_path)
    with open(fallback_path, "rb") as f:
        assert f.read() == b"contenido de prueba"

    os.remove(fallback_path)
