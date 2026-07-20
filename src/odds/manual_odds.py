"""Entrada manual de cuotas (mientras no haya integración automática con una odds API) +
cálculo de probabilidad implícita y valor (edge) contra la probabilidad del modelo.

Punto de extensión: cuando se agregue un proveedor de cuotas real (ej. The Odds API), debería
implementar la misma interfaz que `implied_probability`/`edge` para no tocar el resto del código.
"""
from __future__ import annotations


def implied_probability(decimal_odds: float) -> float:
    """Probabilidad implícita de una cuota decimal (ej. 2.50 -> 40%). No incluye el margen
    de la casa (overround); es la probabilidad "cruda" que implica la cuota."""
    if decimal_odds <= 1:
        raise ValueError("La cuota decimal debe ser mayor a 1.0")
    return 1 / decimal_odds


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
