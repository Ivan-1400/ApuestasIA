from src.models.parlay import (
    Pick,
    best_pick_for_mlb,
    best_pick_for_soccer,
    check_pick_hit,
    most_likely_parlays,
    parlay_status,
)


def test_combined_probability_is_product_of_legs():
    picks = [Pick("A@B", "B", 0.5, "home_win"), Pick("C@D", "D", 0.4, "away_win")]
    parlays = most_likely_parlays(picks, min_legs=2, max_legs=2)
    assert len(parlays) == 1
    assert abs(parlays[0]["combined_probability"] - 0.2) < 1e-9


def test_parlays_sorted_descending_by_probability():
    picks = [
        Pick("A@B", "B", 0.9, "home_win"),
        Pick("C@D", "D", 0.8, "away_win"),
        Pick("E@F", "F", 0.2, "away_win"),
    ]
    parlays = most_likely_parlays(picks, min_legs=2, max_legs=2)
    probs = [p["combined_probability"] for p in parlays]
    assert probs == sorted(probs, reverse=True)


def test_respects_min_and_max_legs():
    picks = [Pick(f"M{i}", "X", 0.6, "home_win") for i in range(5)]
    parlays = most_likely_parlays(picks, min_legs=3, max_legs=3, top_n=100)
    assert all(p["num_legs"] == 3 for p in parlays)


def test_top_n_limits_results():
    picks = [Pick(f"M{i}", "X", 0.6, "home_win") for i in range(5)]
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
        "total_runs_xg": 9.1,
        "home_pitcher_name": "Gerrit Cole",
        "home_pitcher_era": 3.1,
        "away_pitcher_name": "Chris Sale",
        "away_pitcher_era": 2.8,
        "is_final": True,
        "home_score": 6,
        "away_score": 4,
    }
    pick = best_pick_for_mlb(prediction)
    assert pick.outcome_label == "Más de 8.5 carreras"
    assert pick.probability == 0.7
    assert pick.market == "over"
    assert pick.line == 8.5
    assert "9.1 carreras esperadas" in pick.detail
    assert "Gerrit Cole" in pick.detail and "Chris Sale" in pick.detail
    assert pick.is_final is True
    assert pick.home_score == 6
    assert pick.away_score == 4


def test_best_pick_for_soccer_picks_highest_probability_option():
    prediction = {
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "p_home_win": 0.5,
        "p_draw": 0.25,
        "p_away_win": 0.25,
        "p_over_2_5": 0.4,
        "p_under_2_5": 0.6,
        "home_xg": 1.2,
        "away_xg": 0.9,
    }
    pick = best_pick_for_soccer(prediction)
    assert pick.outcome_label == "Under 2.5 goles"
    assert pick.probability == 0.6
    assert pick.market == "under"
    assert pick.line == 2.5
    assert pick.detail == "1.2-0.9 goles esperados"
    assert pick.is_final is False


def test_check_pick_hit_home_win():
    pick = Pick("A@B", "B", 0.6, "home_win")
    assert check_pick_hit(pick, home_score=5, away_score=3) is True
    assert check_pick_hit(pick, home_score=2, away_score=3) is False


def test_check_pick_hit_away_win():
    pick = Pick("A@B", "A", 0.6, "away_win")
    assert check_pick_hit(pick, home_score=2, away_score=5) is True
    assert check_pick_hit(pick, home_score=5, away_score=2) is False


def test_check_pick_hit_draw():
    pick = Pick("A vs B", "Empate", 0.3, "draw")
    assert check_pick_hit(pick, home_score=1, away_score=1) is True
    assert check_pick_hit(pick, home_score=1, away_score=0) is False


def test_check_pick_hit_over_under():
    over_pick = Pick("A vs B", "Over 2.5 goles", 0.5, "over", 2.5)
    under_pick = Pick("A vs B", "Under 2.5 goles", 0.5, "under", 2.5)
    assert check_pick_hit(over_pick, home_score=2, away_score=1) is True
    assert check_pick_hit(over_pick, home_score=1, away_score=1) is False
    assert check_pick_hit(under_pick, home_score=1, away_score=1) is True
    assert check_pick_hit(under_pick, home_score=2, away_score=1) is False


def test_parlay_status_won_when_all_legs_final_and_hit():
    legs = [
        Pick("A@B", "B", 0.6, "home_win", is_final=True, home_score=5, away_score=3),
        Pick("C@D", "C", 0.6, "home_win", is_final=True, home_score=2, away_score=1),
    ]
    assert parlay_status(legs) == "ganado"


def test_parlay_status_lost_if_any_finished_leg_missed():
    legs = [
        Pick("A@B", "B", 0.6, "home_win", is_final=True, home_score=5, away_score=3),
        Pick("C@D", "C", 0.6, "home_win", is_final=True, home_score=1, away_score=2),  # falló
        Pick("E@F", "E", 0.6, "home_win", is_final=False),  # todavía sin jugar
    ]
    assert parlay_status(legs) == "perdido"


def test_parlay_status_pending_when_no_misses_but_some_not_final():
    legs = [
        Pick("A@B", "B", 0.6, "home_win", is_final=True, home_score=5, away_score=3),
        Pick("C@D", "C", 0.6, "home_win", is_final=False),
    ]
    assert parlay_status(legs) == "en_curso"
