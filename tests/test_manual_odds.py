from src.odds.manual_odds import (
    compare_to_market,
    edge,
    expected_value,
    implied_probability,
    implied_probability_american,
)


def test_implied_probability_decimal():
    assert abs(implied_probability(2.0) - 0.5) < 1e-9
    assert abs(implied_probability(4.0) - 0.25) < 1e-9


def test_implied_probability_american_favorite_negative():
    # -131: probabilidad = 131 / 231
    assert abs(implied_probability_american(-131) - (131 / 231)) < 1e-9


def test_implied_probability_american_underdog_positive():
    # +109: probabilidad = 100 / 209
    assert abs(implied_probability_american(109) - (100 / 209)) < 1e-9


def test_implied_probability_american_even_money():
    assert abs(implied_probability_american(100) - 0.5) < 1e-9


def test_edge_positive_when_model_more_confident():
    assert edge(0.6, 2.0) > 0  # modelo 60% vs cuota que implica 50%


def test_expected_value_positive_when_edge_positive():
    assert expected_value(0.6, 2.0, stake=100) > 0


def test_compare_to_market_coincide():
    assert compare_to_market(0.52, 0.50) == "coincide"


def test_compare_to_market_mas_confiado():
    assert compare_to_market(0.65, 0.50) == "mas_confiado"


def test_compare_to_market_menos_confiado():
    assert compare_to_market(0.40, 0.55) == "menos_confiado"
