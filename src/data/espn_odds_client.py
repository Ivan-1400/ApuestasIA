"""Cuotas reales de casas de apuestas, vía la misma API interna (no oficial) de ESPN que ya
usa `espn_client.py`. ESPN embebe la cuota del proveedor prioritario (normalmente DraftKings)
en el endpoint de resumen de cada partido — gratis, sin key.

⚠️ Misma advertencia que espn_client.py: no es un producto documentado, puede cambiar sin
aviso. Si un partido todavía no tiene cuotas publicadas (común para partidos lejanos en el
calendario), simplemente no hay nada que comparar — no es un error.
"""
from __future__ import annotations

import requests

BASE_URL = "https://site.api.espn.com/apis/site/v2/sports"


def get_scoreboard_events(sport_path: str, date: str) -> list[dict]:
    """Eventos crudos del scoreboard de ESPN para una fecha. `sport_path` ej. 'baseball/mlb',
    'soccer/eng.1', 'soccer/mex.1'."""
    date_str = date.replace("-", "")
    resp = requests.get(
        f"{BASE_URL}/{sport_path}/scoreboard",
        params={"dates": date_str},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("events", [])


def find_event_id(events: list[dict], home_team: str, away_team: str) -> str | None:
    """Busca, entre eventos de ESPN, el que coincide por nombre de equipo local/visitante —
    para partidos que vienen de una fuente distinta a ESPN (MLB Stats API, football-data.org)
    y no comparten ID. Comparación tolerante (substring, case-insensitive) porque cada fuente
    nombra los equipos un poco distinto (ej. "Arsenal FC" vs "Arsenal")."""

    def norm(name: str) -> str:
        return name.lower().strip()

    def same(espn_name: str, other_name: str) -> bool:
        espn_name, other_name = norm(espn_name), norm(other_name)
        return espn_name == other_name or espn_name in other_name or other_name in espn_name

    for event in events:
        comp = event["competitions"][0]
        home = next(c for c in comp["competitors"] if c["homeAway"] == "home")
        away = next(c for c in comp["competitors"] if c["homeAway"] == "away")
        if same(home["team"].get("displayName", ""), home_team) and same(
            away["team"].get("displayName", ""), away_team
        ):
            return event["id"]
    return None


def get_odds_by_event(sport_path: str, event_id: str) -> dict | None:
    """Cuotas del proveedor prioritario para un partido puntual. None si todavía no hay
    cuotas publicadas."""
    resp = requests.get(
        f"{BASE_URL}/{sport_path}/summary",
        params={"event": event_id},
        timeout=10,
    )
    resp.raise_for_status()
    pickcenter = resp.json().get("pickcenter")
    if not pickcenter:
        return None

    odds = pickcenter[0]
    return {
        "provider": (odds.get("provider") or {}).get("name"),
        "home_moneyline": (odds.get("homeTeamOdds") or {}).get("moneyLine"),
        "away_moneyline": (odds.get("awayTeamOdds") or {}).get("moneyLine"),
        "draw_moneyline": (odds.get("drawOdds") or {}).get("moneyLine"),
        "total_line": odds.get("overUnder"),
        "over_odds": odds.get("overOdds"),
        "under_odds": odds.get("underOdds"),
    }


if __name__ == "__main__":
    import datetime

    today = datetime.date.today().isoformat()
    events = get_scoreboard_events("baseball/mlb", today)
    print(f"MLB eventos hoy: {len(events)}")
    if events:
        odds = get_odds_by_event("baseball/mlb", events[0]["id"])
        print("Cuotas del primer partido:", odds)
