"""Cache local en SQLite: partidos, stats de equipos y predicciones generadas."""
from __future__ import annotations

import datetime
import os
import shutil
import tempfile

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.orm import Session, declarative_base, sessionmaker

Base = declarative_base()

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "apuestas.sqlite")
DB_PATH = os.path.abspath(DB_PATH)


def _resolve_writable_db_path(path: str) -> str:
    """Streamlit Community Cloud monta el checkout del repo como solo lectura, así que
    escribir en `data/apuestas.sqlite` ahí falla con "attempt to write a readonly database".
    Localmente y en el workflow de GitHub Actions el directorio sí es escribible.

    Si no se puede escribir en `path`, se copia (si existe) a un directorio temporal
    escribible y se usa esa copia para la sesión — los cambios no vuelven al repo desde acá;
    de mantener el historial persistente entre reinicios se encarga el cron diario de
    GitHub Actions, que sí corre en un entorno escribible."""
    directory = os.path.dirname(path)
    probe = os.path.join(directory, ".write_test")
    try:
        with open(probe, "w") as f:
            f.write("x")
        os.remove(probe)
        return path
    except OSError:
        fallback_path = os.path.join(tempfile.gettempdir(), "apuestasia_apuestas.sqlite")
        if os.path.exists(path) and not os.path.exists(fallback_path):
            shutil.copy2(path, fallback_path)
        return fallback_path


class Fixture(Base):
    __tablename__ = "fixtures"

    id = Column(String, primary_key=True)  # f"{sport}:{external_id}"
    sport = Column(String, nullable=False)  # 'soccer' | 'mlb'
    league = Column(String, nullable=False)
    date = Column(String, nullable=False)  # ISO date YYYY-MM-DD
    home_team = Column(String, nullable=False)
    away_team = Column(String, nullable=False)
    home_team_id = Column(String, nullable=True)
    away_team_id = Column(String, nullable=True)
    home_score = Column(Integer, nullable=True)
    away_score = Column(Integer, nullable=True)
    status = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)


class TeamStats(Base):
    __tablename__ = "team_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sport = Column(String, nullable=False)
    league = Column(String, nullable=False)
    season = Column(Integer, nullable=False)
    team_id = Column(String, nullable=False)
    team_name = Column(String, nullable=False)
    games_played = Column(Integer, nullable=False, default=0)
    goals_for_avg = Column(Float, nullable=False, default=0.0)
    goals_against_avg = Column(Float, nullable=False, default=0.0)
    home_goals_for_avg = Column(Float, nullable=True)
    home_goals_against_avg = Column(Float, nullable=True)
    away_goals_for_avg = Column(Float, nullable=True)
    away_goals_against_avg = Column(Float, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)


class Prediction(Base):
    """La pick más probable de un partido, guardada UNA sola vez (la primera vez que se vio),
    para poder medir después si el modelo acertó sin que los recálculos posteriores la pisen."""

    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fixture_id = Column(String, nullable=False, unique=True)
    sport = Column(String, nullable=False)  # 'mlb' | 'soccer'
    match_label = Column(String, nullable=False)
    outcome_label = Column(String, nullable=False)
    market = Column(String, nullable=False)  # 'home_win' | 'away_win' | 'draw' | 'over' | 'under'
    line = Column(Float, nullable=True)
    probability = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


_engine = None
_SessionLocal = None


def init_db() -> None:
    global _engine, _SessionLocal
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    effective_path = _resolve_writable_db_path(DB_PATH)
    _engine = create_engine(f"sqlite:///{effective_path}")
    Base.metadata.create_all(_engine)
    _SessionLocal = sessionmaker(bind=_engine)


def get_session() -> Session:
    if _SessionLocal is None:
        init_db()
    return _SessionLocal()


def upsert_fixture(session: Session, fixture: Fixture) -> None:
    existing = session.get(Fixture, fixture.id)
    if existing:
        for column in Fixture.__table__.columns.keys():
            if column == "id":
                continue
            setattr(existing, column, getattr(fixture, column))
        existing.updated_at = datetime.datetime.utcnow()
    else:
        session.add(fixture)
    session.commit()


def upsert_team_stats(session: Session, stats: TeamStats, staleness_hours: int = 24) -> None:
    existing = (
        session.query(TeamStats)
        .filter_by(sport=stats.sport, league=stats.league, season=stats.season, team_id=stats.team_id)
        .first()
    )
    if existing:
        for column in TeamStats.__table__.columns.keys():
            if column == "id":
                continue
            setattr(existing, column, getattr(stats, column))
        existing.updated_at = datetime.datetime.utcnow()
    else:
        session.add(stats)
    session.commit()


def get_fresh_team_stats(
    session: Session, sport: str, league: str, season: int, team_id: str, staleness_hours: int = 24
) -> TeamStats | None:
    row = (
        session.query(TeamStats)
        .filter_by(sport=sport, league=league, season=season, team_id=team_id)
        .first()
    )
    if row is None:
        return None
    age = datetime.datetime.utcnow() - row.updated_at
    if age > datetime.timedelta(hours=staleness_hours):
        return None
    return row


def save_prediction_once(session: Session, prediction: Prediction) -> None:
    """Guarda la predicción solo si todavía no hay una para ese fixture_id — no pisa la pick
    original con recálculos de días/sesiones posteriores."""
    existing = session.query(Prediction).filter_by(fixture_id=prediction.fixture_id).first()
    if existing is None:
        session.add(prediction)
        session.commit()


def get_fixtures_by_date(session: Session, sport: str, date: str) -> list[Fixture]:
    return session.query(Fixture).filter_by(sport=sport, date=date).all()


if __name__ == "__main__":
    init_db()
    print(f"Base de datos inicializada en {_resolve_writable_db_path(DB_PATH)}")
