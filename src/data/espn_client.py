"""Cliente para la API interna (no oficial) que usa ESPN para sus propias páginas de
resultados. No requiere API key.

⚠️ Advertencia: no es un producto público documentado por ESPN — es la que alimenta su sitio
web, sin garantía de estabilidad ni límite de uso publicado. Se usa acá porque no hay ninguna
fuente oficial gratis con datos de temporada actual para Liga MX ni MLS (ver football_client.py
para las 5 ligas top de Europa, que sí tienen fuente oficial). Si esta API cambia o deja de
responder, esas dos ligas simplemente vuelven a mostrar "sin datos" — no afecta al resto.

Normaliza la respuesta al mismo shape que football_client.py (homeTeam/awayTeam/crest/etc.)
para que pipeline.py no tenga que distinguir la fuente.
"""
from __future__ import annotations

import requests

SCOREBOARD_BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer"
STANDINGS_BASE_URL = "https://site.api.espn.com/apis/v2/sports/soccer"


class EspnClientError(RuntimeError):
    pass


def _normalize_team(team: dict) -> dict:
    return {"id": int(team["id"]), "name": team.get("displayName") or team.get("name"), "crest": team.get("logo")}


def get_fixtures(league_slug: str, date: str) -> list[dict]:
    """Partidos de una fecha puntual (YYYY-MM-DD). `league_slug` es el código ESPN de la
    liga, ej. 'mex.1' (Liga MX) o 'usa.1' (MLS)."""
    date_str = date.replace("-", "")
    resp = requests.get(
        f"{SCOREBOARD_BASE_URL}/{league_slug}/scoreboard",
        params={"dates": f"{date_str}-{date_str}"},
        timeout=10,
    )
    resp.raise_for_status()
    events = resp.json().get("events", [])

    fixtures = []
    for event in events:
        comp = event["competitions"][0]
        home = next(c for c in comp["competitors"] if c["homeAway"] == "home")
        away = next(c for c in comp["competitors"] if c["homeAway"] == "away")
        is_final = comp["status"]["type"]["name"] == "STATUS_FULL_TIME"

        fixtures.append(
            {
                "id": event["id"],
                "homeTeam": _normalize_team(home["team"]),
                "awayTeam": _normalize_team(away["team"]),
                "score": {
                    "fullTime": {
                        "home": int(home["score"]) if is_final and home.get("score") is not None else None,
                        "away": int(away["score"]) if is_final and away.get("score") is not None else None,
                    }
                },
                "status": "FINISHED" if is_final else comp["status"]["type"]["name"],
            }
        )
    return fixtures


def get_standings(league_slug: str) -> list[dict]:
    """Tabla de posiciones (goles a favor/en contra/partidos jugados) de la liga. MLS viene
    dividida en conferencias (Este/Oeste); se juntan todas en una sola lista."""
    resp = requests.get(f"{STANDINGS_BASE_URL}/{league_slug}/standings", timeout=10)
    resp.raise_for_status()
    data = resp.json()

    rows = []
    groups = data.get("children") or [data]
    for group in groups:
        entries = (group.get("standings") or {}).get("entries") or []
        for entry in entries:
            stats = {s["name"]: s.get("value") for s in entry.get("stats", [])}
            rows.append(
                {
                    "team": _normalize_team(entry["team"]),
                    "playedGames": int(stats.get("gamesPlayed") or 0),
                    "goalsFor": int(stats.get("pointsFor") or 0),
                    "goalsAgainst": int(stats.get("pointsAgainst") or 0),
                }
            )
    return rows


if __name__ == "__main__":
    import datetime

    today = datetime.date.today().isoformat()
    for slug, name in (("mex.1", "Liga MX"), ("usa.1", "MLS")):
        fixtures = get_fixtures(slug, today)
        standings = get_standings(slug)
        print(f"{name}: {len(fixtures)} partidos hoy, {len(standings)} equipos en tabla")
