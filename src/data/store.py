"""Cache local en SQLite: partidos, stats de equipos y predicciones generadas."""
from __future__ import annotations

import datetime
import os

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
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fixture_id = Column(String, nullable=False)
    market = Column(String, nullable=False)  # ej. 'total_goals', '1x2_home', 'moneyline_home'
    value = Column(Float, nullable=True)  # valor esperado (ej. goles esperados)
    probability = Column(Float, nullable=True)  # probabilidad del mercado, si aplica
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


_engine = None
_SessionLocal = None


def init_db() -> None:
    global _engine, _SessionLocal
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    _engine = create_engine(f"sqlite:///{DB_PATH}")
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


def save_prediction(session: Session, prediction: Prediction) -> None:
    session.add(prediction)
    session.commit()


def get_fixtures_by_date(session: Session, sport: str, date: str) -> list[Fixture]:
    return session.query(Fixture).filter_by(sport=sport, date=date).all()


if __name__ == "__main__":
    init_db()
    print(f"Base de datos inicializada en {DB_PATH}")
