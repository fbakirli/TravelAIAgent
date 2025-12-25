from agents.flight_finder import FlightFinderAgent
from models.preferences import TravelPreferences
from datetime import date

prefs = TravelPreferences(
    origin_city="GYD",
    destinations=["IST"],
    num_days=4,
    num_locations=1,
    total_budget=350,
    start_date=date(2026, 1, 10)
)

agent = FlightFinderAgent()
flights = agent.run(prefs)

for flight in flights:
    print(flight)
