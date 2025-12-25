import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.hotel_finder_agent import HotelFinderAgent
from models.preferences import TravelPreferences
from datetime import date

# Sample user preferences
prefs = TravelPreferences(
    origin_city="GYD",  # not used by HotelFinder, still required
    destinations=["Istanbul"],
    num_days=3,
    num_locations=1,
    total_budget=600,
    start_date=date(2025, 12, 27),
    end_date=date(2025, 12, 30)
)

# Instantiate and run the agent
agent = HotelFinderAgent()
hotels = agent.run(prefs)

# Display results
print("\n🏨 Hotel Results:")
print("-" * 60)
for hotel in hotels:
    print(f"{hotel.name} ({hotel.rating}⭐ - {hotel.reviews} reviews)")
    print(f"  📍 {hotel.location} | 💵 ${hotel.price}")
    print(f"  🛏️ {hotel.check_in} → {hotel.check_out}")
    print(f"  🔗 {hotel.link}")
    print("-" * 60)

