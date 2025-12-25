import os
import requests
from datetime import timedelta
from typing import Dict, List
from models.preferences import TravelPreferences
from models.flight import FlightOption
from models.hotel import HotelOption
from dotenv import load_dotenv

class HotelFinderAgent:
    """
    Searches for hotels using SerpApi's Google Hotels engine.
    Returns structured hotel options filtered by budget, dates, and location.
    """
    def __init__(self, serpapi_key: str = None):
        load_dotenv()
        self.api_key = serpapi_key or os.getenv("SERPAPI_KEY")
        if not self.api_key:
            raise ValueError("Missing SERPAPI_KEY. Set it in .env or pass to constructor.")

    def run(self, prefs: TravelPreferences, flights: List[FlightOption] = None) -> List[HotelOption]:
        if not prefs.start_date or not prefs.end_date:
            raise ValueError("start_date and end_date are required for hotel search")

        per_city_dates = self._per_city_date_ranges(prefs, flights or [])
        results = []
        for dest, (check_in, check_out) in per_city_dates.items():
            print(f"🏨 Searching hotels in {dest} from {check_in} to {check_out}")
            hotels = self._query_serpapi(
                location_query=dest,
                check_in=check_in,
                check_out=check_out,
                max_price=(prefs.total_budget / prefs.num_days) if prefs.num_days else prefs.total_budget
            )
            results.extend(hotels)
        return results

    def _query_serpapi(self, location_query: str, check_in: str, check_out: str, max_price: float) -> List[HotelOption]:
        url = "https://serpapi.com/search"
        params = {
            "engine": "google_hotels",
            "q": location_query,
            "check_in_date": check_in,
            "check_out_date": check_out,
            "currency": "USD",
            "api_key": self.api_key,
            # Use SerpApi's price filter to limit results by budget (per night):
            "max_price": int(max_price)
        }

        try:
            res = requests.get(url, params=params, timeout=10)
            res.raise_for_status()
        except requests.RequestException as e:
            print(f"❌ Hotel API error for {location_query}: {e}")
            return []

        data = res.json()
        hotels = []

        for h in data.get("properties", []):
            # Extract the nightly price (as a float) from the JSON.
            price_value = h.get("rate_per_night", {}).get("extracted_lowest")
            if price_value is None:
                # Skip this listing if no price is available.
                continue
            price = float(price_value)
            if price > max_price:
                # Skip hotels that exceed the budget per night.
                continue

            # Build the HotelOption with correct field mappings.
            hotels.append(HotelOption(
                name     = h.get("name", "Unknown"),
                location = location_query,
                check_in = check_in,
                check_out= check_out,
                price    = price,
                rating   = float(h.get("overall_rating", 0) or 0),
                reviews  = int(h.get("reviews", 0) or 0),
                link     = h.get("link", "")
            ))
        print(f"✅ Found {len(hotels)} hotels in {location_query}")
        return hotels

    def _per_city_date_ranges(self, prefs: TravelPreferences, flights: List[FlightOption]) -> Dict[str, tuple]:
        """
        Spread the trip dates across destinations so each city gets its own hotel check-in/check-out.
        If flights are provided, align stays with leg departure dates.
        """
        if len(prefs.destinations) <= 1:
            return {
                prefs.destinations[0]: (
                    prefs.start_date.strftime("%Y-%m-%d"),
                    prefs.end_date.strftime("%Y-%m-%d"),
                )
            }

        leg_dates = self._leg_dates(prefs)

        per_city: Dict[str, tuple] = {}
        for idx, city in enumerate(prefs.destinations):
            check_in_dt = leg_dates[min(idx, len(leg_dates) - 1)]
            if idx + 1 < len(prefs.destinations):
                check_out_dt = leg_dates[min(idx + 1, len(leg_dates) - 1)]
            else:
                check_out_dt = prefs.end_date or (check_in_dt + timedelta(days=max(1, prefs.num_days)))

            per_city[city] = (
                check_in_dt.strftime("%Y-%m-%d"),
                check_out_dt.strftime("%Y-%m-%d"),
            )

        return per_city

    def _leg_dates(self, prefs: TravelPreferences):
        num_cities = max(1, len(prefs.destinations))
        total_days = max(1, prefs.num_days)
        base = total_days // num_cities
        remainder = total_days % num_cities

        dates = []
        current = prefs.start_date
        for i in range(num_cities):
            dates.append(current)
            step = base + (1 if i < remainder else 0)
            current = current + timedelta(days=step)
        return dates
