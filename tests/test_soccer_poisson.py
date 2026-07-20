from src.models.soccer_poisson import TeamGoalProfile, expected_goals, match_probabilities


def test_stronger_attacker_has_higher_expected_goals():
    strong = TeamGoalProfile(goals_for_avg=2.5, goals_against_avg=0.8)
    weak = TeamGoalProfile(goals_for_avg=0.8, goals_against_avg=2.0)
    league_avg_home, league_avg_away = 1.5, 1.1

    home_xg, away_xg = expected_goals(strong, weak, league_avg_home, league_avg_away)
    assert home_xg > away_xg


def test_match_probabilities_sum_to_one():
    home = TeamGoalProfile(goals_for_avg=1.6, goals_against_avg=1.1)
    away = TeamGoalProfile(goals_for_avg=1.2, goals_against_avg=1.3)
    home_xg, away_xg = expected_goals(home, away, 1.5, 1.1)

    result = match_probabilities(home_xg, away_xg)
    total = result["p_home_win"] + result["p_draw"] + result["p_away_win"]
    assert abs(total - 1.0) < 1e-6


def test_over_under_probabilities_sum_to_one():
    home = TeamGoalProfile(goals_for_avg=1.6, goals_against_avg=1.1)
    away = TeamGoalProfile(goals_for_avg=1.2, goals_against_avg=1.3)
    home_xg, away_xg = expected_goals(home, away, 1.5, 1.1)

    result = match_probabilities(home_xg, away_xg)
    assert abs(result["p_over_2_5"] + result["p_under_2_5"] - 1.0) < 1e-6


def test_much_stronger_team_favored_to_win():
    strong = TeamGoalProfile(goals_for_avg=2.8, goals_against_avg=0.6)
    weak = TeamGoalProfile(goals_for_avg=0.6, goals_against_avg=2.2)
    home_xg, away_xg = expected_goals(strong, weak, 1.5, 1.1)

    result = match_probabilities(home_xg, away_xg)
    assert result["p_home_win"] > result["p_away_win"]
    assert result["p_home_win"] > result["p_draw"]
