import pytest
from agents.travel_preferences import TravelPreferencesAgent
from datetime import date


def test_all_fields_provided():
    agent = TravelPreferencesAgent()
    input_data = {
        "origin_city": "Baku",
        "destinations": ["Berlin", "Munich"],
        "num_days": 7,
        "num_locations": 2,
        "total_budget": 1400,
        "start_date": "2026-01-05"
    }

    prefs = agent.run(input_data)
    assert prefs.origin_city == "Baku"
    assert prefs.destinations == ["Berlin", "Munich"]
    assert prefs.num_days == 7
    assert prefs.total_budget == 1400
    assert prefs.start_date == date(2026, 1, 5)
    assert prefs.end_date == date(2026, 1, 12)


def test_partial_input_only_destination():
    agent = TravelPreferencesAgent()
    input_data = {
        "destinations": ["Rome"]
    }

    prefs = agent.run(input_data)
    assert prefs.origin_city == "Baku"  # default
    assert prefs.num_days == 5          # default
    assert prefs.total_budget == 1000.0 # default
    assert prefs.destinations == ["Rome"]
    assert prefs.start_date is not None
    assert prefs.end_date == prefs.start_date + prefs.num_days * date.resolution


def test_only_budget():
    agent = TravelPreferencesAgent()
    prefs = agent.run({"total_budget": 500})
    assert prefs.total_budget == 500
    assert len(prefs.destinations) > 0
    assert prefs.start_date is not None


def test_empty_input_defaults_all():
    agent = TravelPreferencesAgent()
    prefs = agent.run({})
    assert prefs.origin_city == "Baku"
    assert prefs.destinations == ["Istanbul", "Tbilisi", "Dubai"]
    assert prefs.num_days == 5
    assert prefs.total_budget == 1000.0
    assert prefs.start_date is not None
    assert prefs.end_date == prefs.start_date + prefs.num_days * date.resolution


def test_invalid_num_days_falls_back_to_default():
    agent = TravelPreferencesAgent()
    prefs = agent.run({
        "num_days": "not_a_number",
        "origin_city": "Baku"
    })
    assert prefs.num_days == 5
