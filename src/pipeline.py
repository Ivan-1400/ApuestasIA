"""Orquesta: traer partidos -> actualizar/cachear stats de equipos -> correr el modelo ->
guardar predicciones. Devuelve listas de dicts listas para mostrar en el dashboard."""
from __future__ import annotations

import datetime

from src.data import espn_client, espn_odds_client, football_client, mlb_client, store
from src.models import mlb_model, soccer_poisson
from src.models.parlay import Pick, best_pick_for_mlb, best_pick_for_soccer, check_pick_hit
from src.odds import manual_odds

DEFAULT_MLB_LEAGUE_AVG_RUNS = 4.3  # promedio histórico aproximado de carreras por equipo/partido
DEFAULT_SOCCER_LEAGUE_AVG_GOALS = 1.35  # promedio histórico aproximado de ligas top europeas

# Ambos clientes exponen get_fixtures(code, date) / get_standings(code) con el mismo shape de
# respuesta, así que build_soccer_predictions puede elegir uno u otro sin ramas especiales.
SOCCER_CLIENTS = {"football_data": football_client, "espn": espn_client}

# Para partidos que no vienen de ESPN (football-data.org), hace falta el slug de ESPN
# equivalente para poder buscar sus cuotas por nombre de equipo.
ESPN_SOCCER_SLUGS = {
    "PL": "eng.1",
    "PD": "esp.1",
    "SA": "ita.1",
    "BL1": "ger.1",
    "CL": "uefa.champions",
}


def _attach_market_odds(result: dict, pick, sport_path: str, event_id: str | None) -> None:
    """Agrega la cuota real de mercado (DraftKings vía ESPN) al resultado y compara la pick
    del modelo contra ella. Best-effort: sin cuota publicada o cualquier error de red se
    ignora en silencio — no es un partido con problema, simplemente no hay nada que comparar."""
    result["market_provider"] = None
    result["market_probability"] = None
    result["market_comparison"] = None
    if not event_id:
        return
    try:
        odds = espn_odds_client.get_odds_by_event(sport_path, str(event_id))
    except Exception:
        return
    if not odds:
        return

    if pick.market in ("over", "under"):
        market_moneyline = odds.get("over_odds" if pick.market == "over" else "under_odds")
    else:
        market_moneyline = {
            "home_win": odds.get("home_moneyline"),
            "away_win": odds.get("away_moneyline"),
            "draw": odds.get("draw_moneyline"),
        }.get(pick.market)

    if market_moneyline is None:
        return

    market_probability = manual_odds.implied_probability_american(market_moneyline)
    result["market_provider"] = odds.get("provider")
    result["market_probability"] = market_probability
    result["market_comparison"] = manual_odds.compare_to_market(pick.probability, market_probability)


def build_mlb_predictions(date: str | None = None) -> list[dict]:
    date = date or datetime.date.today().isoformat()
    season = int(date[:4])
    session = store.get_session()
    try:
        games = mlb_client.get_schedule(date, hydrate_probable_pitcher=True)

        try:
            espn_events = espn_odds_client.get_scoreboard_events("baseball/mlb", date)
        except Exception:
            espn_events = []

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
            home_score = g["teams"]["home"].get("score")
            away_score = g["teams"]["away"].get("score")
            status = g["status"]["detailedState"]
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
                    home_score=home_score,
                    away_score=away_score,
                    status=status,
                ),
            )

            result = {
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
                "status": status,
                "is_final": status in ("Final", "Game Over"),
                "home_score": home_score,
                "away_score": away_score,
                **prediction,
            }

            pick = best_pick_for_mlb(result)
            store.save_prediction_once(
                session,
                store.Prediction(
                    fixture_id=fixture_id,
                    sport="mlb",
                    match_label=pick.match_label,
                    outcome_label=pick.outcome_label,
                    market=pick.market,
                    line=pick.line,
                    probability=pick.probability,
                ),
            )

            espn_event_id = espn_odds_client.find_event_id(espn_events, home["name"], away["name"])
            _attach_market_odds(result, pick, "baseball/mlb", espn_event_id)

            results.append(result)
        return results
    finally:
        session.close()


def build_soccer_predictions(
    competition_code: str,
    league_name: str,
    season: int,
    date: str | None = None,
    source: str = "football_data",
) -> list[dict]:
    date = date or datetime.date.today().isoformat()
    client = SOCCER_CLIENTS[source]
    session = store.get_session()
    try:
        fixtures = client.get_fixtures(competition_code, date)

        # Cuotas: si la liga ya viene de ESPN, cada fixture trae su propio ID de ESPN, no hace
        # falta buscar nada. Si viene de football-data.org, hay que ubicar el evento equivalente
        # en ESPN por nombre de equipo (mismo mecanismo que en build_mlb_predictions).
        espn_sport_path = None
        espn_events = []
        if source == "espn":
            espn_sport_path = f"soccer/{competition_code}"
        elif competition_code in ESPN_SOCCER_SLUGS:
            espn_sport_path = f"soccer/{ESPN_SOCCER_SLUGS[competition_code]}"
            try:
                espn_events = espn_odds_client.get_scoreboard_events(espn_sport_path, date)
            except Exception:
                espn_events = []

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
            for row in client.get_standings(competition_code):
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
            home_score = full_time.get("home")
            away_score = full_time.get("away")
            status = f.get("status")
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
                    home_score=home_score,
                    away_score=away_score,
                    status=status,
                ),
            )

            result = {
                "fixture_id": fixture_id,
                "date": date,
                "home_team": home["name"],
                "away_team": away["name"],
                "home_team_logo": home.get("crest"),
                "away_team_logo": away.get("crest"),
                "status": status,
                "is_final": status == "FINISHED",
                "home_score": home_score,
                "away_score": away_score,
                **prediction,
            }

            pick = best_pick_for_soccer(result)
            store.save_prediction_once(
                session,
                store.Prediction(
                    fixture_id=fixture_id,
                    sport="soccer",
                    match_label=pick.match_label,
                    outcome_label=pick.outcome_label,
                    market=pick.market,
                    line=pick.line,
                    probability=pick.probability,
                ),
            )

            if espn_sport_path:
                event_id = f["id"] if source == "espn" else espn_odds_client.find_event_id(
                    espn_events, home["name"], away["name"]
                )
                _attach_market_odds(result, pick, espn_sport_path, event_id)
            else:
                result["market_provider"] = None
                result["market_probability"] = None
                result["market_comparison"] = None

            results.append(result)
        return results
    finally:
        session.close()


def get_track_record(sport: str | None = None) -> dict:
    """Resumen histórico de las picks guardadas: cuántas ya se pueden verificar (el partido
    terminó), de esas cuántas acertaron, y el % de acierto acumulado."""
    session = store.get_session()
    try:
        query = session.query(store.Prediction)
        if sport:
            query = query.filter_by(sport=sport)
        predictions = query.order_by(store.Prediction.created_at.desc()).all()

        hits = 0
        misses = 0
        pending = 0
        rows = []
        for pred in predictions:
            fixture = session.get(store.Fixture, pred.fixture_id)
            decided = (
                fixture is not None and fixture.home_score is not None and fixture.away_score is not None
            )
            if not decided:
                pending += 1
                rows.append(
                    {
                        "match_label": pred.match_label,
                        "outcome_label": pred.outcome_label,
                        "probability": pred.probability,
                        "hit": None,
                    }
                )
                continue

            pick = Pick(pred.match_label, pred.outcome_label, pred.probability, pred.market, pred.line)
            hit = check_pick_hit(pick, fixture.home_score, fixture.away_score)
            hits += hit
            misses += not hit
            rows.append(
                {
                    "match_label": pred.match_label,
                    "outcome_label": pred.outcome_label,
                    "probability": pred.probability,
                    "hit": hit,
                    "home_score": fixture.home_score,
                    "away_score": fixture.away_score,
                }
            )

        decided_count = hits + misses
        return {
            "total": len(predictions),
            "hits": hits,
            "misses": misses,
            "pending": pending,
            "hit_rate": hits / decided_count if decided_count else None,
            "rows": rows,
        }
    finally:
        session.close()
