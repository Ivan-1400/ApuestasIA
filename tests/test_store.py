import os
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


def test_resolve_writable_db_path_falls_back_when_file_itself_is_readonly(tmp_path, monkeypatch):
    """Simula el caso real de Streamlit Cloud: el directorio permite crear archivos nuevos
    (capa de escritura del contenedor) pero el archivo `apuestas.sqlite` del checkout de git
    está en la capa de solo lectura — probar con un archivo separado daba falso positivo."""
    db_path = tmp_path / "apuestas.sqlite"
    db_path.write_bytes(b"contenido de prueba")

    real_open = open

    def fake_open(path, mode="r", *args, **kwargs):
        if os.path.abspath(str(path)) == os.path.abspath(str(db_path)) and "a" in mode:
            raise OSError("readonly filesystem")
        return real_open(path, mode, *args, **kwargs)

    monkeypatch.setattr("builtins.open", fake_open)

    fallback_path = os.path.join(tempfile.gettempdir(), "apuestasia_apuestas.sqlite")
    if os.path.exists(fallback_path):
        os.remove(fallback_path)

    result = store._resolve_writable_db_path(str(db_path))

    assert result == fallback_path
    assert os.path.exists(fallback_path)
    with open(fallback_path, "rb") as f:
        assert f.read() == b"contenido de prueba"

    os.remove(fallback_path)
