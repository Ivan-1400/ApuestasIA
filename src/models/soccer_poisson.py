"""Modelo de Poisson para fútbol (estilo Dixon-Coles simplificado, sin el ajuste de correlación
de marcadores bajos). Da fuerza de ataque/defensa por equipo y de ahí probabilidades de mercados
típicos de casas de apuestas: 1X2, goles totales (over/under), BTTS, marcador más probable."""
from __future__ import annotations

from dataclasses import dataclass

from scipy.stats import poisson


@dataclass
class TeamGoalProfile:
    """Promedios de goles de un equipo, separados en local/visitante."""

    goals_for_avg: float
    goals_against_avg: float


def expected_goals(
    home: TeamGoalProfile,
    away: TeamGoalProfile,
    league_avg_home_goals: float,
    league_avg_away_goals: float,
) -> tuple[float, float]:
    """Devuelve (xG local, xG visitante) combinando fuerza de ataque y defensa contra el
    promedio de la liga. Fórmula estándar del modelo de Poisson para fútbol."""
    home_attack = home.goals_for_avg / league_avg_home_goals if league_avg_home_goals else 0.0
    home_defense = home.goals_against_avg / league_avg_away_goals if league_avg_away_goals else 0.0
    away_attack = away.goals_for_avg / league_avg_away_goals if league_avg_away_goals else 0.0
    away_defense = away.goals_against_avg / league_avg_home_goals if league_avg_home_goals else 0.0

    home_xg = home_attack * away_defense * league_avg_home_goals
    away_xg = away_attack * home_defense * league_avg_away_goals
    return home_xg, away_xg


def score_matrix(home_xg: float, away_xg: float, max_goals: int = 10) -> list[list[float]]:
    """Matriz [goles_local][goles_visitante] con la probabilidad de cada marcador exacto."""
    home_probs = [poisson.pmf(g, home_xg) for g in range(max_goals + 1)]
    away_probs = [poisson.pmf(g, away_xg) for g in range(max_goals + 1)]
    return [[hp * ap for ap in away_probs] for hp in home_probs]


def match_probabilities(home_xg: float, away_xg: float, max_goals: int = 10) -> dict:
    """Probabilidades derivadas: 1X2, over/under 2.5, ambos anotan, marcador más probable."""
    matrix = score_matrix(home_xg, away_xg, max_goals)

    p_home_win = sum(
        matrix[h][a] for h in range(max_goals + 1) for a in range(max_goals + 1) if h > a
    )
    p_draw = sum(matrix[h][h] for h in range(max_goals + 1))
    p_away_win = sum(
        matrix[h][a] for h in range(max_goals + 1) for a in range(max_goals + 1) if h < a
    )

    p_over_2_5 = sum(
        matrix[h][a]
        for h in range(max_goals + 1)
        for a in range(max_goals + 1)
        if h + a > 2.5
    )
    p_btts = sum(
        matrix[h][a] for h in range(1, max_goals + 1) for a in range(1, max_goals + 1)
    )

    best_score = max(
        ((h, a) for h in range(max_goals + 1) for a in range(max_goals + 1)),
        key=lambda ha: matrix[ha[0]][ha[1]],
    )

    return {
        "home_xg": home_xg,
        "away_xg": away_xg,
        "total_xg": home_xg + away_xg,
        "p_home_win": p_home_win,
        "p_draw": p_draw,
        "p_away_win": p_away_win,
        "p_over_2_5": p_over_2_5,
        "p_under_2_5": 1 - p_over_2_5,
        "p_btts": p_btts,
        "most_likely_score": best_score,
        "most_likely_score_prob": matrix[best_score[0]][best_score[1]],
    }


if __name__ == "__main__":
    # Ejemplo con equipos ficticios: local fuerte en ataque, visitante flojo en defensa.
    home = TeamGoalProfile(goals_for_avg=2.1, goals_against_avg=0.9)
    away = TeamGoalProfile(goals_for_avg=1.0, goals_against_avg=1.6)
    league_avg_home, league_avg_away = 1.5, 1.1

    hxg, axg = expected_goals(home, away, league_avg_home, league_avg_away)
    result = match_probabilities(hxg, axg)
    for key, value in result.items():
        print(f"{key}: {value}")
