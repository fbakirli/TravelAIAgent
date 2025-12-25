# agents/budget_optimizer_agent.py
from __future__ import annotations

from typing import Dict, List, Tuple
from datetime import datetime

from models.preferences import TravelPreferences
from models.budget import BudgetBreakdown
from models.flight import FlightOption
from models.hotel import HotelOption
from models.itinerary import Itinerary
from utils.airport_codes import CITY_TO_AIRPORT


class BudgetOptimizerAgent:
    """
    Agent #5:
    Filters and selects options to FIT budget before finalizing.
    """

    def __init__(self):
        self._airport_to_city = {v: k for k, v in CITY_TO_AIRPORT.items()}

    def run(
        self,
        prefs: TravelPreferences,
        flights: List[FlightOption],
        hotels: List[HotelOption],
        itinerary: Itinerary,
    ) -> Tuple[List[FlightOption], Dict[str, HotelOption], BudgetBreakdown]:

        nights_per_city = self._nights_per_city(itinerary)
        total_nights = sum(nights_per_city.values()) or max(1, prefs.num_days)

        # ---- FLIGHT FILTERING ----
        multi_city = len(prefs.destinations) > 1
        flights_sorted = sorted(flights, key=self._flight_sort_key)
        chosen_flights: List[FlightOption] = []

        if multi_city:
            origin_label = self._label_city(prefs.origin_city)
            leg_order = []
            current = origin_label
            for dest in itinerary.destinations:
                leg_order.append((current, dest))
                current = dest
            leg_order.append((current, origin_label))

            flights_by_leg: Dict[Tuple[str, str], FlightOption] = {}
            for f in flights_sorted:
                key = (self._label_city(f.origin), self._label_city(f.destination))
                existing = flights_by_leg.get(key)
                if existing is None or self._flight_sort_key(f) < self._flight_sort_key(existing):
                    flights_by_leg[key] = f

            for leg in leg_order:
                if leg in flights_by_leg:
                    chosen_flights.append(flights_by_leg[leg])
        else:
            # Single-destination: keep the cheapest overall (round-trip search result).
            flight_budget = prefs.total_budget * 0.45  # heuristic
            best_in_budget = next((f for f in flights_sorted if f.price <= flight_budget), None)
            chosen_flights = [best_in_budget] if best_in_budget else flights_sorted[:1]

        flight_cost = sum(f.price for f in chosen_flights)

        # ---- HOTEL FILTERING ----
        hotel_budget = max(0.0, prefs.total_budget - flight_cost)
        hotel_budget_per_city: Dict[str, float] = {}
        if nights_per_city:
            for city, n in nights_per_city.items():
                share = n / total_nights
                hotel_budget_per_city[city] = hotel_budget * share
        else:
            per_city = hotel_budget / max(1, len(prefs.destinations))
            hotel_budget_per_city = {self._label_city(city): per_city for city in prefs.destinations}

        chosen_hotels: Dict[str, HotelOption] = {}

        for city in prefs.destinations:
            city_label = self._label_city(city)
            candidates = [
                h for h in hotels
                if self._label_city(h.location) == city_label
                and (h.price * max(1, nights_per_city.get(city_label, 0))) <= hotel_budget_per_city.get(city_label, hotel_budget)
            ]

            if candidates:
                chosen_hotels[city_label] = min(candidates, key=lambda h: h.price)
            else:
                # fallback: cheapest available (but visible over-budget)
                city_hotels = [h for h in hotels if self._label_city(h.location) == city_label]
                if city_hotels:
                    chosen_hotels[city_label] = min(city_hotels, key=lambda h: h.price)

        hotel_cost = sum(
            h.price * max(1, nights_per_city.get(city, 0))
            for city, h in chosen_hotels.items()
        )

        activities_cost = sum(
            a.est_cost
            for day in itinerary.days
            for a in day.activities
        )

        total_spend = flight_cost + hotel_cost + activities_cost
        if total_spend > prefs.total_budget and activities_cost > 0:
            allowed_for_activities = max(0.0, prefs.total_budget - flight_cost - hotel_cost)
            scale = max(0.0, min(1.0, allowed_for_activities / activities_cost))
            if scale < 1.0:
                self._scale_activity_costs(itinerary, scale)
                activities_cost = sum(
                    a.est_cost
                    for day in itinerary.days
                    for a in day.activities
                )
                total_spend = flight_cost + hotel_cost + activities_cost

        budget = BudgetBreakdown(
            flights=float(flight_cost),
            hotels=float(hotel_cost),
            activities=float(activities_cost),
        )

        return chosen_flights, chosen_hotels, budget

    def _nights_per_city(self, itinerary: Itinerary) -> Dict[str, int]:
        nights: Dict[str, int] = {}
        for day in itinerary.days:
            nights[day.city] = nights.get(day.city, 0) + 1
        return nights

    def _scale_activity_costs(self, itinerary: Itinerary, scale: float) -> None:
        for day in itinerary.days:
            for activity in day.activities:
                activity.est_cost = round(activity.est_cost * scale, 2)

    def _label_city(self, value: str) -> str:
        if value in self._airport_to_city:
            return self._airport_to_city[value]
        return value

    def _flight_sort_key(self, flight: FlightOption):
        """
        Sort flights by price, then by parsed departure time when available.
        """
        dep = self._parse_departure_time(flight.departure_time)
        return (flight.price, dep or datetime.max, str(flight.departure_time))

    def _parse_departure_time(self, value: str):
        if not value:
            return None
        v = str(value).strip()
        fmts = [
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M",
            "%H:%M",
            "%I:%M %p",
        ]
        for fmt in fmts:
            try:
                # Use an arbitrary date when only time is provided.
                dt = datetime.strptime(v, fmt)
                if dt.year == 1900:
                    dt = dt.replace(year=2100)
                return dt
            except ValueError:
                continue
        return None
