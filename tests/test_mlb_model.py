from src.models.mlb_model import (
    TeamRunProfile,
    expected_runs,
    log5_win_probability,
    predict_match,
    pythagorean_win_pct,
)


def test_better_offense_defense_scores_more_expected_runs():
    strong = TeamRunProfile(runs_for_avg=5.5, runs_against_avg=3.5)
    weak = TeamRunProfile(runs_for_avg=3.5, runs_against_avg=5.0)

    home_runs, away_runs = expected_runs(strong, weak, 4.5, 4.2)
    assert home_runs > away_runs


def test_pythagorean_win_pct_favors_better_run_differential():
    good_team_pct = pythagorean_win_pct(runs_for=5.0, runs_against=3.5)
    bad_team_pct = pythagorean_win_pct(runs_for=3.5, runs_against=5.0)
    assert good_team_pct > 0.5 > bad_team_pct


def test_log5_symmetry():
    p_a_beats_b = log5_win_probability(0.6, 0.4)
    p_b_beats_a = log5_win_probability(0.4, 0.6)
    assert abs((p_a_beats_b + p_b_beats_a) - 1.0) < 1e-9


def test_predict_match_win_probabilities_sum_to_one():
    home = TeamRunProfile(runs_for_avg=5.1, runs_against_avg=3.8)
    away = TeamRunProfile(runs_for_avg=4.0, runs_against_avg=4.5)
    result = predict_match(home, away, league_avg_home_runs=4.5, league_avg_away_runs=4.2)
    assert abs(result["p_home_win"] + result["p_away_win"] - 1.0) < 1e-9
    assert abs(result["p_over"] + result["p_under"] - 1.0) < 1e-9
