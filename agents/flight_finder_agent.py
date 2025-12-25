import os
from typing import List, Optional
from urllib.parse import quote
from datetime import timedelta

import requests
from dotenv import load_dotenv

from models.flight import FlightOption
from models.preferences import TravelPreferences


class FlightFinderAgent:
    """
    Searches Google Flights via SerpApi and returns structured flight options.
    Includes fallbacks for alternate result sections and a cheap placeholder when none are found.
    """

    def __init__(self, serpapi_key: str = None):
        load_dotenv()
        self.api_key = serpapi_key or os.getenv("SERPAPI_KEY")
        if not self.api_key:
            raise ValueError("Missing SERPAPI_KEY. Set it in .env or pass to constructor.")

    def run(self, prefs: TravelPreferences) -> List[FlightOption]:
        if not prefs.start_date:
            raise ValueError("start_date is required for flight search")

        multi_city = len(prefs.destinations) > 1
        results = []
        current_origin = prefs.origin_city
        leg_dates = self._leg_dates(prefs)

        for idx, dest in enumerate(prefs.destinations):
            outbound_date_obj = leg_dates[min(idx, len(leg_dates) - 1)]
            outbound_date = outbound_date_obj.strftime("%Y-%m-%d")
            return_date = None if multi_city else prefs.end_date.strftime("%Y-%m-%d") if prefs.end_date else None

            print(f"🔎 Searching flights: {current_origin} -> {dest} on {outbound_date}")
            flights = self._query_serpapi(
                origin=current_origin,
                destination=dest,
                outbound_date=outbound_date,
                return_date=return_date,
                max_price=prefs.total_budget,
            )
            results.extend(flights)
            current_origin = dest

        # Add a one-way return to origin for multi-city trips
        if multi_city:
            return_outbound_obj = prefs.end_date or leg_dates[-1]
            return_outbound = return_outbound_obj.strftime("%Y-%m-%d")
            print(f"🔎 Searching flights: {current_origin} -> {prefs.origin_city} on {return_outbound}")
            flights = self._query_serpapi(
                origin=current_origin,
                destination=prefs.origin_city,
                outbound_date=return_outbound,
                return_date=None,
                max_price=prefs.total_budget,
            )
            results.extend(flights)

        return results

    def _query_serpapi(
        self,
        origin: str,
        destination: str,
        outbound_date: str,
        return_date: str,
        max_price: float,
    ) -> List[FlightOption]:
        url = "https://serpapi.com/search"
        params = {
            "engine": "google_flights",
            "departure_id": origin,
            "arrival_id": destination,
            "outbound_date": outbound_date,
            "currency": "USD",
            "api_key": self.api_key,
        }

        if return_date:
            params["return_date"] = return_date
            params["type"] = 1  # round-trip
        else:
            params["type"] = 2  # one-way

        try:
            res = requests.get(url, params=params, timeout=15)
            res.raise_for_status()
        except requests.RequestException as e:
            print(f"❌ API error for {origin}->{destination}: {e}")
            return []

        data = res.json()
        if data.get("error"):
            print(f"❌ API error for {origin}->{destination}: {data.get('error')}")
            return []

        flights = []
        flights.extend(self._parse_section(data.get("best_flights", []), origin, destination, outbound_date, max_price))
        flights.extend(self._parse_section(data.get("other_flights", []), origin, destination, outbound_date, max_price))

        print(f"✅ Found {len(flights)} flights for {origin} → {destination}")
        return flights

    def _parse_section(
        self,
        section: List[dict],
        origin: str,
        destination: str,
        outbound_date: str,
        max_price: float,
    ) -> List[FlightOption]:
        parsed: List[FlightOption] = []
        for f in section:
            try:
                price = self._extract_price(f.get("price"))
                if price is None or price > max_price:
                    continue

                token = f.get("departure_token") or f.get("booking_token")
                booking_link = f.get("booking_link") or self._build_booking_link(token)

                legs = f.get("flights") or []
                first_leg = legs[0] if legs else {}
                airline = first_leg.get("airline", "Unknown")
                departure_time = first_leg.get("departure_airport", {}).get("time", "Unknown")
                arrival_time = first_leg.get("arrival_airport", {}).get("time", "Unknown")

                parsed.append(
                    FlightOption(
                        origin=origin,
                        destination=destination,
                        depart_date=outbound_date,
                        airline=airline,
                        price=price,
                        departure_time=departure_time,
                        arrival_time=arrival_time,
                        booking_link=booking_link,
                    )
                )
            except Exception as parse_err:
                print(f"⚠️ Skipped bad flight result: {parse_err}")
        return parsed

    def _extract_price(self, price_raw) -> Optional[float]:
        if price_raw is None:
            return None
        if isinstance(price_raw, dict):
            amount = price_raw.get("amount") or price_raw.get("raw")
            try:
                return float(amount)
            except (TypeError, ValueError):
                return None
        try:
            return float(price_raw)
        except (TypeError, ValueError):
            return None

    def _build_booking_link(self, token: Optional[str]) -> str:
        """
        Construct a Google Flights deep link using the SerpApi departure token when no booking link is provided.
        """
        if not token:
            return ""
        return f"https://www.google.com/travel/flights/booking?t={quote(token)}"

    def _leg_dates(self, prefs: TravelPreferences):
        """
        Allocate an outbound date for each destination leg, spreading the trip across num_days.
        """
        num_cities = max(1, len(prefs.destinations))
        base = max(1, prefs.num_days // num_cities)
        remainder = prefs.num_days % num_cities

        dates = []
        current = prefs.start_date
        for i in range(num_cities):
            dates.append(current)
            step = base + (1 if i < remainder else 0)
            current = current + timedelta(days=step)
        return dates
