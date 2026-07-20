"""Cliente para football-data.org. Requiere FOOTBALL_DATA_API_KEY en el entorno (.env).

Se eligió sobre API-Football porque el tier gratis de API-Football no da acceso a la temporada
actual en ninguna liga (solo datos históricos 2022-2024) — confirmado contra la API real el
2026-07-19. football-data.org sí da partidos/resultados actuales (con resultado demorado unos
minutos, no en vivo) para un set fijo de competencias en su tier gratis, que no incluye Liga MX
ni MLS — ver `config/leagues.yaml` (`unsupported: true` en esas dos).
"""
from __future__ import annotations

import os

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.football-data.org/v4"


class FootballClientError(RuntimeError):
    pass


def _get_api_key() -> str | None:
    """Busca la key en el entorno (.env local) y, si no está, en st.secrets (Streamlit Cloud)."""
    key = os.environ.get("FOOTBALL_DATA_API_KEY")
    if key:
        return key
    try:
        import streamlit as st

        return st.secrets.get("FOOTBALL_DATA_API_KEY")
    except Exception:
        return None


def _headers() -> dict:
    key = _get_api_key()
    if not key:
        raise FootballClientError(
            "Falta FOOTBALL_DATA_API_KEY. Localmente: copiá .env.example a .env y completá tu API "
            "key gratuita de https://www.football-data.org/client/register. En Streamlit Cloud: "
            "cargala en Settings → Secrets de la app."
        )
    return {"X-Auth-Token": key}


def get_fixtures(competition_code: str, date: str) -> list[dict]:
    """Partidos de una competencia en una fecha puntual (YYYY-MM-DD)."""
    resp = requests.get(
        f"{BASE_URL}/competitions/{competition_code}/matches",
        headers=_headers(),
        params={"dateFrom": date, "dateTo": date},
        timeout=10,
    )
    if resp.status_code == 403:
        raise FootballClientError(
            f"Competencia '{competition_code}' no disponible en el tier gratis de football-data.org"
        )
    resp.raise_for_status()
    return resp.json().get("matches", [])


def get_standings(competition_code: str) -> list[dict]:
    """Tabla de posiciones de la competencia (incluye goalsFor/goalsAgainst/playedGames por
    equipo — de ahí se derivan los promedios de goles que usa el modelo de Poisson)."""
    resp = requests.get(
        f"{BASE_URL}/competitions/{competition_code}/standings",
        headers=_headers(),
        timeout=10,
    )
    if resp.status_code == 403:
        raise FootballClientError(
            f"Competencia '{competition_code}' no disponible en el tier gratis de football-data.org"
        )
    resp.raise_for_status()
    data = resp.json()
    total_table = next(
        (s["table"] for s in data.get("standings", []) if s.get("type") == "TOTAL"), []
    )
    return total_table


if __name__ == "__main__":
    import sys

    try:
        matches = get_fixtures("PL", "2026-07-19")
        standings = get_standings("PL")
    except FootballClientError as exc:
        print(f"No se pudo probar contra la API real: {exc}")
        sys.exit(1)

    print(f"Partidos Premier League 2026-07-19: {len(matches)}")
    print(f"Equipos en la tabla: {len(standings)}")
    for row in standings[:3]:
        print(f"  {row['team']['name']}: {row['goalsFor']}-{row['goalsAgainst']} en {row['playedGames']} partidos")
