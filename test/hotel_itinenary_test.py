import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from datetime import date
from models.preferences import TravelPreferences
from agents.hotel_finder import HotelFinderAgent
from agents.itinerary_planner import ItineraryPlannerAgent

prefs = TravelPreferences(
    origin_city="GYD",
    destinations=["Istanbul"],
    num_days=3,
    num_locations=1,
    total_budget=600,
    start_date=date(2025, 12, 27),
    end_date=date(2025, 12, 30)
)

print("\n Hotel Finder Agent:")
hotel_agent = HotelFinderAgent()
hotels = hotel_agent.run(prefs)
for hotel in hotels:
    print(hotel)

print("\n Itinerary Planner Agent:")
itinerary_agent = ItineraryPlannerAgent()
itinerary = itinerary_agent.run(prefs)
for day in itinerary:
    print(day.date, day.location)
    for item in day.items:
        print(f"  ⏰ {item.time} — {item.activity}")
