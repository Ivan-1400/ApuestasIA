"""Matemática de cuotas: probabilidad implícita, valor (edge) contra la probabilidad del
modelo, y comparación del modelo contra la cuota real de mercado (`espn_odds_client.py`,
DraftKings vía ESPN)."""
from __future__ import annotations

MARKET_AGREEMENT_THRESHOLD = 0.05  # diferencia de probabilidad por debajo de la cual se
# considera que el modelo "coincide" con el mercado, no que discrepa


def implied_probability(decimal_odds: float) -> float:
    """Probabilidad implícita de una cuota decimal (ej. 2.50 -> 40%). No incluye el margen
    de la casa (overround); es la probabilidad "cruda" que implica la cuota."""
    if decimal_odds <= 1:
        raise ValueError("La cuota decimal debe ser mayor a 1.0")
    return 1 / decimal_odds


def implied_probability_american(moneyline: float) -> float:
    """Probabilidad implícita de una cuota en formato americano (ej. -131, +109) — el
    formato que usan las casas de EE.UU. como DraftKings."""
    if moneyline < 0:
        return -moneyline / (-moneyline + 100)
    return 100 / (moneyline + 100)


def compare_to_market(model_probability: float, market_probability: float) -> str:
    """'coincide' | 'mas_confiado' | 'menos_confiado' — qué tan lejos está la probabilidad
    del modelo de la probabilidad implícita del mercado."""
    diff = model_probability - market_probability
    if abs(diff) < MARKET_AGREEMENT_THRESHOLD:
        return "coincide"
    return "mas_confiado" if diff > 0 else "menos_confiado"


def edge(model_probability: float, decimal_odds: float) -> float:
    """Diferencia entre la probabilidad del modelo y la probabilidad implícita de la cuota.
    Positivo = el modelo cree que el mercado está subvalorando ese resultado (posible valor)."""
    return model_probability - implied_probability(decimal_odds)


def expected_value(model_probability: float, decimal_odds: float, stake: float = 1.0) -> float:
    """Valor esperado de apostar `stake` a esa cuota, según la probabilidad del modelo."""
    win_return = stake * (decimal_odds - 1)
    lose_return = -stake
    return model_probability * win_return + (1 - model_probability) * lose_return


if __name__ == "__main__":
    model_p = 0.55
    odds = 2.10
    print(f"Probabilidad implícita: {implied_probability(odds):.2%}")
    print(f"Edge del modelo: {edge(model_p, odds):+.2%}")
    print(f"Valor esperado (stake=1): {expected_value(model_p, odds):+.3f}")
