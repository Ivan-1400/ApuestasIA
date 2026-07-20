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
