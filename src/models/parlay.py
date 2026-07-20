"""Arma parleys (combinadas) a partir de la pick más probable de cada partido.

Asume independencia entre partidos: la probabilidad combinada es el producto de las
probabilidades individuales. Es una simplificación — en la realidad puede haber correlación
entre partidos (ej. clima, calendario de un mismo equipo) — pero es razonable como primera
aproximación y es lo que hacen la mayoría de las calculadoras de parlay simples.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations


@dataclass(frozen=True)
class Pick:
    match_label: str
    outcome_label: str
    probability: float


def best_pick_for_mlb(prediction: dict) -> Pick:
    """Elige, entre moneyline y total de carreras, el resultado con mayor probabilidad."""
    options = [
        (prediction["home_team"], prediction["p_home_win"]),
        (prediction["away_team"], prediction["p_away_win"]),
        (f"Más de {prediction['line']} carreras", prediction["p_over"]),
        (f"Menos de {prediction['line']} carreras", prediction["p_under"]),
    ]
    outcome_label, probability = max(options, key=lambda o: o[1])
    match_label = f"{prediction['away_team']} @ {prediction['home_team']}"
    return Pick(match_label, outcome_label, probability)


def best_pick_for_soccer(prediction: dict) -> Pick:
    """Elige, entre 1X2 y over/under 2.5, el resultado con mayor probabilidad."""
    options = [
        (prediction["home_team"], prediction["p_home_win"]),
        ("Empate", prediction["p_draw"]),
        (prediction["away_team"], prediction["p_away_win"]),
        ("Over 2.5 goles", prediction["p_over_2_5"]),
        ("Under 2.5 goles", prediction["p_under_2_5"]),
    ]
    outcome_label, probability = max(options, key=lambda o: o[1])
    match_label = f"{prediction['home_team']} vs {prediction['away_team']}"
    return Pick(match_label, outcome_label, probability)


def most_likely_parlays(
    picks: list[Pick], min_legs: int = 2, max_legs: int = 4, top_n: int = 5
) -> list[dict]:
    """Combina picks de partidos distintos (de a `min_legs` a `max_legs` patas) y devuelve
    hasta `top_n`, ordenadas por probabilidad combinada descendente."""
    max_legs = min(max_legs, len(picks))
    results = []
    for size in range(min_legs, max_legs + 1):
        for combo in combinations(picks, size):
            combined_probability = 1.0
            for pick in combo:
                combined_probability *= pick.probability
            results.append(
                {"legs": list(combo), "combined_probability": combined_probability, "num_legs": size}
            )
    results.sort(key=lambda r: r["combined_probability"], reverse=True)
    return results[:top_n]


if __name__ == "__main__":
    sample_picks = [
        Pick("A @ B", "B", 0.65),
        Pick("C @ D", "D", 0.60),
        Pick("E @ F", "Más de 8.5", 0.58),
        Pick("G @ H", "G", 0.55),
    ]
    for parlay in most_likely_parlays(sample_picks):
        legs = " + ".join(f"{leg.outcome_label} ({leg.match_label})" for leg in parlay["legs"])
        print(f"{parlay['num_legs']} patas — {parlay['combined_probability']:.1%}: {legs}")
