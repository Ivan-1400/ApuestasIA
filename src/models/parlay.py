"""Arma parleys (combinadas) a partir de la pick más probable de cada partido, y permite
verificar si esa pick acertó una vez que el partido terminó.

Asume independencia entre partidos: la probabilidad combinada es el producto de las
probabilidades individuales. Es una simplificación — en la realidad puede haber correlación
entre partidos (ej. clima, calendario de un mismo equipo) — pero es razonable como primera
aproximación y es lo que hacen la mayoría de las calculadoras de parlay simples.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

Market = str  # 'home_win' | 'away_win' | 'draw' | 'over' | 'under'


@dataclass(frozen=True)
class Pick:
    match_label: str
    outcome_label: str
    probability: float
    market: Market
    line: float | None = None  # solo para 'over'/'under'


def best_pick_for_mlb(prediction: dict) -> Pick:
    """Elige, entre moneyline y total de carreras, el resultado con mayor probabilidad."""
    line = prediction["line"]
    options = [
        (prediction["home_team"], prediction["p_home_win"], "home_win", None),
        (prediction["away_team"], prediction["p_away_win"], "away_win", None),
        (f"Más de {line} carreras", prediction["p_over"], "over", line),
        (f"Menos de {line} carreras", prediction["p_under"], "under", line),
    ]
    outcome_label, probability, market, pick_line = max(options, key=lambda o: o[1])
    match_label = f"{prediction['away_team']} @ {prediction['home_team']}"
    return Pick(match_label, outcome_label, probability, market, pick_line)


def best_pick_for_soccer(prediction: dict) -> Pick:
    """Elige, entre 1X2 y over/under 2.5, el resultado con mayor probabilidad."""
    options = [
        (prediction["home_team"], prediction["p_home_win"], "home_win", None),
        ("Empate", prediction["p_draw"], "draw", None),
        (prediction["away_team"], prediction["p_away_win"], "away_win", None),
        ("Over 2.5 goles", prediction["p_over_2_5"], "over", 2.5),
        ("Under 2.5 goles", prediction["p_under_2_5"], "under", 2.5),
    ]
    outcome_label, probability, market, pick_line = max(options, key=lambda o: o[1])
    match_label = f"{prediction['home_team']} vs {prediction['away_team']}"
    return Pick(match_label, outcome_label, probability, market, pick_line)


def check_pick_hit(pick: Pick, home_score: int, away_score: int) -> bool:
    """Compara una pick contra el resultado final real y devuelve si acertó."""
    total = home_score + away_score
    if pick.market == "home_win":
        return home_score > away_score
    if pick.market == "away_win":
        return away_score > home_score
    if pick.market == "draw":
        return home_score == away_score
    if pick.market == "over":
        return total > pick.line
    if pick.market == "under":
        return total < pick.line
    raise ValueError(f"Mercado desconocido: {pick.market}")


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
        Pick("A @ B", "B", 0.65, "home_win"),
        Pick("C @ D", "D", 0.60, "away_win"),
        Pick("E @ F", "Más de 8.5 carreras", 0.58, "over", 8.5),
        Pick("G @ H", "G", 0.55, "home_win"),
    ]
    for parlay in most_likely_parlays(sample_picks):
        legs = " + ".join(f"{leg.outcome_label} ({leg.match_label})" for leg in parlay["legs"])
        print(f"{parlay['num_legs']} patas — {parlay['combined_probability']:.1%}: {legs}")
