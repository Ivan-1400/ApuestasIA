from src.data.espn_odds_client import find_event_id


def _event(home_name: str, away_name: str, event_id: str = "1") -> dict:
    return {
        "id": event_id,
        "competitions": [
            {
                "competitors": [
                    {"homeAway": "home", "team": {"displayName": home_name}},
                    {"homeAway": "away", "team": {"displayName": away_name}},
                ]
            }
        ],
    }


def test_find_event_id_exact_match():
    events = [_event("Toronto Blue Jays", "Chicago White Sox", "555")]
    assert find_event_id(events, "Toronto Blue Jays", "Chicago White Sox") == "555"


def test_find_event_id_tolerant_substring_match():
    events = [_event("Arsenal", "Chelsea", "777")]
    assert find_event_id(events, "Arsenal FC", "Chelsea FC") == "777"


def test_find_event_id_returns_none_when_no_match():
    events = [_event("Arsenal", "Chelsea", "777")]
    assert find_event_id(events, "Real Madrid", "Barcelona") is None


def test_find_event_id_picks_correct_event_among_several():
    events = [
        _event("Yankees", "Red Sox", "1"),
        _event("Dodgers", "Giants", "2"),
    ]
    assert find_event_id(events, "Dodgers", "Giants") == "2"
