"""Cliente para la MLB Stats API oficial (statsapi.mlb.com). No requiere API key."""
from __future__ import annotations

import requests

BASE_URL = "https://statsapi.mlb.com/api/v1"
SPORT_ID_MLB = 1


def get_schedule(date: str, hydrate_probable_pitcher: bool = False) -> list[dict]:
    """Partidos de una fecha (YYYY-MM-DD). Incluye resultado si ya se jugaron.

    Con `hydrate_probable_pitcher=True`, cada lado (`teams.home`/`teams.away`) trae además
    `probablePitcher: {id, fullName}` cuando ya está anunciado.
    """
    params = {"sportId": SPORT_ID_MLB, "date": date}
    if hydrate_probable_pitcher:
        params["hydrate"] = "probablePitcher"
    resp = requests.get(f"{BASE_URL}/schedule", params=params, timeout=10)
    resp.raise_for_status()
    dates = resp.json().get("dates", [])
    return dates[0]["games"] if dates else []


def get_teams(season: int) -> list[dict]:
    resp = requests.get(
        f"{BASE_URL}/teams",
        params={"sportId": SPORT_ID_MLB, "season": season},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("teams", [])


def get_team_season_stats(team_id: int, season: int, group: str = "hitting") -> dict:
    """group: 'hitting' o 'pitching'. Devuelve el bloque de stats de temporada del equipo."""
    resp = requests.get(
        f"{BASE_URL}/teams/{team_id}/stats",
        params={"stats": "season", "group": group, "season": season},
        timeout=10,
    )
    resp.raise_for_status()
    stats = resp.json().get("stats", [])
    splits = stats[0].get("splits", []) if stats else []
    return splits[0]["stat"] if splits else {}


def get_pitcher_season_era(person_id: int, season: int) -> float | None:
    """ERA de temporada de un lanzador. None si todavía no tiene stats esa temporada."""
    resp = requests.get(
        f"{BASE_URL}/people/{person_id}/stats",
        params={"stats": "season", "group": "pitching", "season": season},
        timeout=10,
    )
    resp.raise_for_status()
    stats = resp.json().get("stats", [])
    splits = stats[0].get("splits", []) if stats else []
    era = splits[0]["stat"].get("era") if splits else None
    return float(era) if era not in (None, "-.--") else None


if __name__ == "__main__":
    import datetime

    today = datetime.date.today().isoformat()
    games = get_schedule(today)
    print(f"Partidos MLB para {today}: {len(games)}")
    for g in games[:5]:
        home = g["teams"]["home"]["team"]["name"]
        away = g["teams"]["away"]["team"]["name"]
        print(f"  {away} @ {home} — status: {g['status']['detailedState']}")
