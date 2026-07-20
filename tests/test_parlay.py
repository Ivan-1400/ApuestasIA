from src.models.parlay import Pick, best_pick_for_mlb, best_pick_for_soccer, most_likely_parlays


def test_combined_probability_is_product_of_legs():
    picks = [Pick("A@B", "B", 0.5), Pick("C@D", "D", 0.4)]
    parlays = most_likely_parlays(picks, min_legs=2, max_legs=2)
    assert len(parlays) == 1
    assert abs(parlays[0]["combined_probability"] - 0.2) < 1e-9


def test_parlays_sorted_descending_by_probability():
    picks = [
        Pick("A@B", "B", 0.9),
        Pick("C@D", "D", 0.8),
        Pick("E@F", "F", 0.2),
    ]
    parlays = most_likely_parlays(picks, min_legs=2, max_legs=2)
    probs = [p["combined_probability"] for p in parlays]
    assert probs == sorted(probs, reverse=True)


def test_respects_min_and_max_legs():
    picks = [Pick(f"M{i}", "X", 0.6) for i in range(5)]
    parlays = most_likely_parlays(picks, min_legs=3, max_legs=3, top_n=100)
    assert all(p["num_legs"] == 3 for p in parlays)


def test_top_n_limits_results():
    picks = [Pick(f"M{i}", "X", 0.6) for i in range(5)]
    parlays = most_likely_parlays(picks, min_legs=2, max_legs=4, top_n=3)
    assert len(parlays) == 3


def test_best_pick_for_mlb_picks_highest_probability_option():
    prediction = {
        "home_team": "Yankees",
        "away_team": "Red Sox",
        "p_home_win": 0.55,
        "p_away_win": 0.45,
        "p_over": 0.7,
        "p_under": 0.3,
        "line": 8.5,
    }
    pick = best_pick_for_mlb(prediction)
    assert pick.outcome_label == "Más de 8.5 carreras"
    assert pick.probability == 0.7


def test_best_pick_for_soccer_picks_highest_probability_option():
    prediction = {
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "p_home_win": 0.5,
        "p_draw": 0.25,
        "p_away_win": 0.25,
        "p_over_2_5": 0.4,
        "p_under_2_5": 0.6,
    }
    pick = best_pick_for_soccer(prediction)
    assert pick.outcome_label == "Under 2.5 goles"
    assert pick.probability == 0.6
