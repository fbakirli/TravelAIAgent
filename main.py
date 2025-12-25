# main.py
from __future__ import annotations
from datetime import date

from agents.travel_agent import TravelAgent
from models.preferences import TravelPreferences

if __name__ == "__main__":
    prefs = TravelPreferences(
        origin_city="GYD",
        destinations=["Tbilisi"],
        num_days=4,
        num_locations=1,
        total_budget=350,
        start_date=date(2026, 3, 5),
    )

    agent = TravelAgent()
    print(agent.run(prefs))
