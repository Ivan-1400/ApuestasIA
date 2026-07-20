"""Orquesta: traer partidos -> actualizar/cachear stats de equipos -> correr el modelo ->
guardar predicciones. Devuelve listas de dicts listas para mostrar en el dashboard."""
from __future__ import annotations

import datetime

from src.data import football_client, mlb_client, store
from src.models import mlb_model, soccer_poisson

DEFAULT_MLB_LEAGUE_AVG_RUNS = 4.3  # promedio histórico aproximado de carreras por equipo/partido
DEFAULT_SOCCER_LEAGUE_AVG_GOALS = 1.35  # promedio histórico aproximado de ligas top europeas


def build_mlb_predictions(date: str | None = None) -> list[dict]:
    date = date or datetime.date.today().isoformat()
    season = int(date[:4])
    session = store.get_session()
    try:
        games = mlb_client.get_schedule(date, hydrate_probable_pitcher=True)

        team_ids = {g["teams"]["home"]["team"]["id"] for g in games} | {
            g["teams"]["away"]["team"]["id"] for g in games
        }

        profiles: dict[int, mlb_model.TeamRunProfile] = {}
        for team_id in team_ids:
            cached = store.get_fresh_team_stats(session, "mlb", "MLB", season, str(team_id))
            if cached:
                profiles[team_id] = mlb_model.TeamRunProfile(
                    cached.goals_for_avg, cached.goals_against_avg
                )
                continue

            hitting = mlb_client.get_team_season_stats(team_id, season, "hitting")
            pitching = mlb_client.get_team_season_stats(team_id, season, "pitching")
            games_played = int(hitting.get("gamesPlayed") or 1)
            runs_for_avg = float(hitting.get("runs", 0)) / games_played
            runs_against_avg = float(pitching.get("runs", 0)) / games_played

            profiles[team_id] = mlb_model.TeamRunProfile(runs_for_avg, runs_against_avg)
            store.upsert_team_stats(
                session,
                store.TeamStats(
                    sport="mlb",
                    league="MLB",
                    season=season,
                    team_id=str(team_id),
                    team_name=str(team_id),
                    games_played=games_played,
                    goals_for_avg=runs_for_avg,
                    goals_against_avg=runs_against_avg,
                ),
            )

        league_avg_runs = (
            sum(p.runs_for_avg for p in profiles.values()) / len(profiles)
            if profiles
            else DEFAULT_MLB_LEAGUE_AVG_RUNS
        )

        pitcher_era_cache: dict[int, float | None] = {}

        def pitcher_info(side: dict) -> tuple[str | None, float | None]:
            probable = side.get("probablePitcher")
            if not probable:
                return None, None
            pitcher_id = probable["id"]
            if pitcher_id not in pitcher_era_cache:
                pitcher_era_cache[pitcher_id] = mlb_client.get_pitcher_season_era(pitcher_id, season)
            return probable["fullName"], pitcher_era_cache[pitcher_id]

        results = []
        for g in games:
            home = g["teams"]["home"]["team"]
            away = g["teams"]["away"]["team"]
            home_profile = profiles.get(
                home["id"], mlb_model.TeamRunProfile(league_avg_runs, league_avg_runs)
            )
            away_profile = profiles.get(
                away["id"], mlb_model.TeamRunProfile(league_avg_runs, league_avg_runs)
            )

            prediction = mlb_model.predict_match(
                home_profile, away_profile, league_avg_runs, league_avg_runs
            )

            home_pitcher_name, home_pitcher_era = pitcher_info(g["teams"]["home"])
            away_pitcher_name, away_pitcher_era = pitcher_info(g["teams"]["away"])

            fixture_id = f"mlb:{g['gamePk']}"
            store.upsert_fixture(
                session,
                store.Fixture(
                    id=fixture_id,
                    sport="mlb",
                    league="MLB",
                    date=date,
                    home_team=home["name"],
                    away_team=away["name"],
                    home_team_id=str(home["id"]),
                    away_team_id=str(away["id"]),
                    home_score=g["teams"]["home"].get("score"),
                    away_score=g["teams"]["away"].get("score"),
                    status=g["status"]["detailedState"],
                ),
            )

            results.append(
                {
                    "fixture_id": fixture_id,
                    "date": date,
                    "home_team": home["name"],
                    "away_team": away["name"],
                    "home_team_logo": f"https://www.mlbstatic.com/team-logos/{home['id']}.svg",
                    "away_team_logo": f"https://www.mlbstatic.com/team-logos/{away['id']}.svg",
                    "home_pitcher_name": home_pitcher_name,
                    "home_pitcher_era": home_pitcher_era,
                    "away_pitcher_name": away_pitcher_name,
                    "away_pitcher_era": away_pitcher_era,
                    **prediction,
                }
            )
        return results
    finally:
        session.close()


def build_soccer_predictions(
    competition_code: str, league_name: str, season: int, date: str | None = None
) -> list[dict]:
    date = date or datetime.date.today().isoformat()
    session = store.get_session()
    try:
        fixtures = football_client.get_fixtures(competition_code, date)

        team_ids = {f[side]["id"] for f in fixtures for side in ("homeTeam", "awayTeam")}

        profiles: dict[int, soccer_poisson.TeamGoalProfile] = {}
        missing_team_ids = []
        for team_id in team_ids:
            cached = store.get_fresh_team_stats(session, "soccer", league_name, season, str(team_id))
            if cached:
                profiles[team_id] = soccer_poisson.TeamGoalProfile(
                    cached.goals_for_avg, cached.goals_against_avg
                )
            else:
                missing_team_ids.append(team_id)

        if missing_team_ids:
            # La tabla de posiciones trae goalsFor/goalsAgainst/playedGames de TODOS los
            # equipos en un solo request, así que se cachean todos aunque solo falten algunos.
            for row in football_client.get_standings(competition_code):
                team_id = row["team"]["id"]
                games_played = row["playedGames"] or 1
                goals_for = row["goalsFor"] / games_played
                goals_against = row["goalsAgainst"] / games_played

                profiles[team_id] = soccer_poisson.TeamGoalProfile(goals_for, goals_against)
                store.upsert_team_stats(
                    session,
                    store.TeamStats(
                        sport="soccer",
                        league=league_name,
                        season=season,
                        team_id=str(team_id),
                        team_name=row["team"]["name"],
                        games_played=games_played,
                        goals_for_avg=goals_for,
                        goals_against_avg=goals_against,
                    ),
                )

        league_avg_goals = (
            sum(p.goals_for_avg for p in profiles.values()) / len(profiles)
            if profiles
            else DEFAULT_SOCCER_LEAGUE_AVG_GOALS
        )

        results = []
        for f in fixtures:
            home = f["homeTeam"]
            away = f["awayTeam"]
            home_profile = profiles.get(
                home["id"], soccer_poisson.TeamGoalProfile(league_avg_goals, league_avg_goals)
            )
            away_profile = profiles.get(
                away["id"], soccer_poisson.TeamGoalProfile(league_avg_goals, league_avg_goals)
            )

            home_xg, away_xg = soccer_poisson.expected_goals(
                home_profile, away_profile, league_avg_goals, league_avg_goals
            )
            prediction = soccer_poisson.match_probabilities(home_xg, away_xg)

            full_time = (f.get("score", {}) or {}).get("fullTime", {}) or {}
            fixture_id = f"soccer:{f['id']}"
            store.upsert_fixture(
                session,
                store.Fixture(
                    id=fixture_id,
                    sport="soccer",
                    league=league_name,
                    date=date,
                    home_team=home["name"],
                    away_team=away["name"],
                    home_team_id=str(home["id"]),
                    away_team_id=str(away["id"]),
                    home_score=full_time.get("home"),
                    away_score=full_time.get("away"),
                    status=f.get("status"),
                ),
            )

            results.append(
                {
                    "fixture_id": fixture_id,
                    "date": date,
                    "home_team": home["name"],
                    "away_team": away["name"],
                    "home_team_logo": home.get("crest"),
                    "away_team_logo": away.get("crest"),
                    **prediction,
                }
            )
        return results
    finally:
        session.close()
