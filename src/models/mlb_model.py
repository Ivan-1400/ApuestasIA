"""Modelo de carreras para MLB: total de carreras vía Poisson (igual enfoque que el modelo de
goles de fútbol) + probabilidad de ganar vía Pythagorean win expectation y log5 para el
enfrentamiento directo. Son las dos fórmulas estándar de sabermetría para esto."""
from __future__ import annotations

from dataclasses import dataclass

from scipy.stats import poisson

PYTHAGOREAN_EXPONENT = 1.83  # exponente calculado empíricamente por Bill James / Clay Davenport


@dataclass
class TeamRunProfile:
    runs_for_avg: float
    runs_against_avg: float


def expected_runs(
    home: TeamRunProfile,
    away: TeamRunProfile,
    league_avg_home_runs: float,
    league_avg_away_runs: float,
) -> tuple[float, float]:
    """Devuelve (carreras esperadas local, visitante), mismo enfoque que expected_goals."""
    home_offense = home.runs_for_avg / league_avg_home_runs if league_avg_home_runs else 0.0
    home_defense = home.runs_against_avg / league_avg_away_runs if league_avg_away_runs else 0.0
    away_offense = away.runs_for_avg / league_avg_away_runs if league_avg_away_runs else 0.0
    away_defense = away.runs_against_avg / league_avg_home_runs if league_avg_home_runs else 0.0

    home_runs = home_offense * away_defense * league_avg_home_runs
    away_runs = away_offense * home_defense * league_avg_away_runs
    return home_runs, away_runs


def pythagorean_win_pct(runs_for: float, runs_against: float) -> float:
    """Expectativa de % de victorias de un equipo a partir de sus carreras a favor/en contra."""
    if runs_for == 0 and runs_against == 0:
        return 0.5
    rf_exp = runs_for**PYTHAGOREAN_EXPONENT
    ra_exp = runs_against**PYTHAGOREAN_EXPONENT
    return rf_exp / (rf_exp + ra_exp)


def log5_win_probability(team_a_win_pct: float, team_b_win_pct: float) -> float:
    """Probabilidad de que el equipo A le gane al equipo B, dado el % de victorias de cada uno
    (fórmula log5 de Bill James)."""
    numerator = team_a_win_pct - team_a_win_pct * team_b_win_pct
    denominator = team_a_win_pct + team_b_win_pct - 2 * team_a_win_pct * team_b_win_pct
    if denominator == 0:
        return 0.5
    return numerator / denominator


def total_runs_probabilities(home_runs: float, away_runs: float, line: float = 8.5) -> dict:
    """Probabilidad de over/under sobre una línea de carreras totales (default 8.5, típico MLB)."""
    max_runs = 20
    home_probs = [poisson.pmf(r, home_runs) for r in range(max_runs + 1)]
    away_probs = [poisson.pmf(r, away_runs) for r in range(max_runs + 1)]
    p_over = 0.0
    for h in range(max_runs + 1):
        for a in range(max_runs + 1):
            if h + a > line:
                p_over += home_probs[h] * away_probs[a]
    return {"p_over": p_over, "p_under": 1 - p_over, "line": line}


def predict_match(
    home: TeamRunProfile,
    away: TeamRunProfile,
    league_avg_home_runs: float,
    league_avg_away_runs: float,
    total_line: float = 8.5,
) -> dict:
    home_runs, away_runs = expected_runs(home, away, league_avg_home_runs, league_avg_away_runs)

    home_win_pct = pythagorean_win_pct(home.runs_for_avg, home.runs_against_avg)
    away_win_pct = pythagorean_win_pct(away.runs_for_avg, away.runs_against_avg)
    p_home_win = log5_win_probability(home_win_pct, away_win_pct)

    totals = total_runs_probabilities(home_runs, away_runs, total_line)

    return {
        "home_runs_xg": home_runs,
        "away_runs_xg": away_runs,
        "total_runs_xg": home_runs + away_runs,
        "p_home_win": p_home_win,
        "p_away_win": 1 - p_home_win,
        **totals,
    }


if __name__ == "__main__":
    home = TeamRunProfile(runs_for_avg=5.1, runs_against_avg=3.8)
    away = TeamRunProfile(runs_for_avg=4.0, runs_against_avg=4.5)
    result = predict_match(home, away, league_avg_home_runs=4.5, league_avg_away_runs=4.2)
    for key, value in result.items():
        print(f"{key}: {value}")
