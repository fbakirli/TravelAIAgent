import requests
from datetime import datetime

class TravelDataClient:
    """
    A client for fetching travel data (flights and hotels) from SerpApi's Google Travel Explore API.
    Uses SerpApi's Google Travel Explore API (engine `google_travel_explore`) to retrieve flight prices, trip dates, durations, and lodging estimates:contentReference[oaicite:0]{index=0}.
    """
    BASE_URL = "https://serpapi.com/search"

    def __init__(self, api_key: str):
        """Initialize the travel data client with the given SerpApi API key."""
        self.api_key = api_key
        self.default_params = {
            "engine": "google_travel_explore",
            "hl": "en",
            "gl": "us",
            "currency": "USD",
            "api_key": self.api_key
        }

    def search_one_way_flight(self, origin: str, destination: str, date: datetime):
        """
        Search for a one-way flight from origin to destination on the given date.
        Returns a dict with flight price and duration (in minutes), or None if not found.
        """
        params = self.default_params.copy()
        params.update({
            "departure_id": origin,
            "arrival_id": destination,
            "outbound_date": date.strftime("%Y-%m-%d"),
            "type": "2"  # one-way flight
        })
        try:
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"Error fetching flight data for {origin}->{destination} on {date.date()}: {e}")
            return None
        flight_info = {}
        if data.get("flights"):
            flights = data["flights"]
            if flights:
                flight = flights[0]
                price = flight.get("price")
                duration = flight.get("duration") or flight.get("flight_duration")
                flight_info = {
                    "price": float(price) if price is not None else None,
                    "duration_minutes": int(duration) if duration is not None else None
                }
        elif data.get("destinations"):
            # If result is under 'destinations' (e.g., Explore mode), find matching entry
            for dest in data["destinations"]:
                if dest.get("destination_airport", {}).get("code") == destination or dest.get("name", "").lower() == destination.lower():
                    flight_info = {
                        "price": float(dest.get("flight_price")) if dest.get("flight_price") is not None else None,
                        "duration_minutes": int(dest.get("flight_duration")) if dest.get("flight_duration") is not None else None
                    }
                    break
        return flight_info if flight_info else None

    def get_destination_info(self, origin: str, region_id: str, start_date, end_date):
        """
        Fetch destination exploration data from origin to a broad region between start_date and end_date.
        Returns a list of destinations with flight and hotel prices in that region (could be empty if none found).
        """
        params = self.default_params.copy()
        params.update({
            "departure_id": origin,
            "arrival_area_id": region_id,
            "outbound_date": start_date.strftime("%Y-%m-%d"),
            "return_date": end_date.strftime("%Y-%m-%d"),
            "type": "1"  # round-trip search
        })
        try:
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"Error fetching destination info for region {region_id}: {e}")
            return []
        return data.get("destinations", [])
