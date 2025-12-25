# agents/itinerary_planner_agent.py
from __future__ import annotations

from datetime import timedelta
from typing import Dict, List, Optional

from clients.attractions_client import AttractionsClient
from clients.tripadvisor_client import TravelGuideInfo
from models.flight import FlightOption
from models.hotel import HotelOption
from models.itinerary import Activity, Itinerary, ItineraryDay
from models.preferences import TravelPreferences
from utils.airport_codes import CITY_TO_AIRPORT


class ItineraryPlannerAgent:
    """
    Agent #4:
    Builds a day-by-day plan that follows real city order, uses available flights/hotels,
    and keeps activities inside the remaining budget envelope.
    """

    def __init__(self):
        self.attractions = AttractionsClient()
        self._airport_to_city = {v: k for k, v in CITY_TO_AIRPORT.items()}

    def run(
        self,
        prefs: TravelPreferences,
        flights: List[FlightOption],
        hotels: List[HotelOption],
        travel_guides: Optional[Dict[str, TravelGuideInfo]] = None,
    ) -> Itinerary:
        if not prefs.start_date:
            raise ValueError("start_date required for itinerary planning")

        travel_guides = travel_guides or {}
        ordered_cities = self._build_city_route(prefs, flights)
        days_per_city = self._allocate_days(prefs.num_days, ordered_cities)
        activity_budget_per_day = self._estimate_activity_budget(
            prefs, flights, hotels, days_per_city
        )

        current_date = prefs.start_date
        itinerary_days: List[ItineraryDay] = []
        prev_city = prefs.origin_city

        for city in ordered_cities:
            days_in_city = days_per_city[city]
            for day_idx in range(days_per_city[city]):
                transport = None
                activities: List[Activity] = []

                if day_idx == 0:
                    leg = self._find_leg(prev_city, city, flights)
                    if leg:
                        transport = (
                            f"{self._label_city(leg.origin)} → {self._label_city(leg.destination)} "
                            f"with {leg.airline} ({leg.departure_time}–{leg.arrival_time})"
                        )
                        transfer_cost = self._ground_transfer_cost(activity_budget_per_day)
                        activities.append(
                            Activity(
                                name="Airport/ground transfer",
                                description="Local bus/metro/taxi from airport to hotel (price varies)",
                                est_cost=transfer_cost,
                            )
                        )
                    else:
                        transport = f"Travel to {self._label_city(city)} (train/bus recommended)"
                        intercity_cost = self._intercity_transport_cost(activity_budget_per_day)
                        activities.append(
                            Activity(
                                name="Intercity transport",
                                description=f"Train/bus transfer to {self._label_city(city)} (price varies)",
                                est_cost=intercity_cost,
                            )
                        )

                    hotel_name = self._choose_hotel_name(city, hotels)
                    if hotel_name:
                        activities.append(
                            Activity(
                                name="Hotel check-in",
                                description=f"Check in at {hotel_name}",
                                est_cost=0.0,
                            )
                        )

                activities.extend(
                    self._activities_for_city(
                        city=city,
                        budget_per_day=activity_budget_per_day,
                        day_offset=day_idx,
                        days_in_city=days_in_city,
                        travel_guide=travel_guides.get(city),
                    )
                )
                activities = self._fit_to_budget(activities, activity_budget_per_day)

                itinerary_days.append(
                    ItineraryDay(
                        date=current_date,
                        city=self._label_city(city),
                        activities=activities,
                        transport=transport,
                    )
                )
                current_date += timedelta(days=1)

            prev_city = city

        return Itinerary(
            origin=self._label_city(prefs.origin_city),
            destinations=[self._label_city(c) for c in ordered_cities],
            days=itinerary_days,
        )

    # ----------------------
    # helpers
    # ----------------------

    def _build_city_route(
        self, prefs: TravelPreferences, flights: List[FlightOption]
    ) -> List[str]:
        """
        Prefer real flight destinations; fall back to user-provided order.
        """
        origin_label = self._label_city(prefs.origin_city)
        route: List[str] = []

        for f in sorted(flights, key=lambda x: x.depart_date or ""):
            city = self._label_city(f.destination)
            if city == origin_label:
                # Skip the return-to-origin leg when building the visiting route.
                continue
            if city not in route:
                route.append(city)

        for dest in prefs.destinations:
            city = self._label_city(dest)
            if city == origin_label:
                continue
            if city not in route:
                route.append(city)

        filtered = [c for c in route if c != origin_label]
        if filtered:
            return filtered
        # Fallback to destinations (still excluding origin city).
        return [self._label_city(d) for d in prefs.destinations if self._label_city(d) != origin_label]

    def _allocate_days(self, total_days: int, cities: List[str]) -> Dict[str, int]:
        total_days = max(1, total_days)
        base = total_days // len(cities)
        remainder = total_days % len(cities)

        allocation: Dict[str, int] = {}
        for i, city in enumerate(cities):
            allocation[city] = base + (1 if i < remainder else 0)

        return allocation

    def _estimate_activity_budget(
        self,
        prefs: TravelPreferences,
        flights: List[FlightOption],
        hotels: List[HotelOption],
        days_per_city: Dict[str, int],
    ) -> float:
        cheapest_flight = min((f.price for f in flights), default=0.0)

        hotel_floor = 0.0
        for city, nights in days_per_city.items():
            price = self._cheapest_hotel_price(city, hotels)
            hotel_floor += price * max(1, nights)

        remaining = prefs.total_budget - cheapest_flight - hotel_floor
        if remaining <= 0:
            return 0.0

        total_days = sum(days_per_city.values()) or 1
        return remaining / total_days

    def _activities_for_city(
        self,
        city: str,
        budget_per_day: float,
        day_offset: int,
        days_in_city: int,
        travel_guide: Optional[TravelGuideInfo],
    ) -> List[Activity]:
        city_label = self._label_city(city)
        pool_size = min(30, max(6, days_in_city * 3))
        attractions = []
        if travel_guide and getattr(travel_guide, "attractions", None):
            attractions = travel_guide.attractions[:pool_size]
        if not attractions:
            attractions = self.attractions.top_attractions(city_label, limit=pool_size)
        if not attractions:
            return []

        start = (day_offset * 3) % len(attractions)
        selected = []
        for i in range(3):
            idx = (start + i) % len(attractions)
            selected.append(attractions[idx])

        slots = [("Morning", 0.32), ("Afternoon", 0.28), ("Evening", 0.22), ("Late", 0.18)]
        slots = slots[: len(selected)]

        activities: List[Activity] = []

        # Local transport pass for the day (only if budget allows)
        transport_cost = self._local_transport_cost(budget_per_day, travel_guide)
        if transport_cost and transport_cost > 0:
            activities.append(
                Activity(
                    name="Getting around",
                    description="Metro/tram/bus (typical single ride)",
                    est_cost=transport_cost,
                )
            )

        for idx, (slot_label, share) in enumerate(slots):
            item = selected[idx % len(selected)]
            name = item.get("name")
            link = item.get("link") or None
            est = round(max(0.0, budget_per_day * share), 2)
            desc = item.get("description") or ""
            activities.append(
                Activity(
                    name=f"{slot_label}: {name}",
                    description=desc,
                    est_cost=est,
                    link=link,
                )
            )

        return activities

    def _find_leg(
        self, origin: str, destination: str, flights: List[FlightOption]
    ) -> Optional[FlightOption]:
        for f in flights:
            if self._label_city(f.destination) == self._label_city(destination) and self._label_city(
                f.origin
            ) == self._label_city(origin):
                return f
        return None

    def _choose_hotel_name(self, city: str, hotels: List[HotelOption]) -> str:
        city_label = self._label_city(city)
        matches = [h for h in hotels if self._label_city(h.location) == city_label]
        if not matches:
            return ""
        return min(matches, key=lambda h: h.price).name

    def _cheapest_hotel_price(self, city: str, hotels: List[HotelOption]) -> float:
        city_label = self._label_city(city)
        prices = [h.price for h in hotels if self._label_city(h.location) == city_label]
        return min(prices) if prices else 0.0

    def _local_transport_cost(self, budget_per_day: float, guide) -> float:
        fare = None
        if guide is not None and getattr(guide, "transit_fare", None) is not None:
            fare = guide.transit_fare
        if fare is None:
            return 0.0
        # Use the real single-ride fare; keep it inside daily budget.
        if budget_per_day <= 0:
            return 0.0
        return min(round(fare, 2), budget_per_day)

    def _ground_transfer_cost(self, budget_per_day: float) -> float:
        # No reliable live pricing available here; keep zero cost to avoid fabrication.
        return 0.0

    def _intercity_transport_cost(self, budget_per_day: float) -> float:
        # No reliable live pricing available here; keep zero cost to avoid fabrication.
        return 0.0

    def _fit_to_budget(self, activities: List[Activity], budget_per_day: float) -> List[Activity]:
        paid = [a for a in activities if a.est_cost > 0]
        total = sum(a.est_cost for a in paid)
        if total <= max(budget_per_day, 0):
            return activities
        if total == 0:
            return activities

        scale = budget_per_day / total if total else 1.0
        for act in paid:
            act.est_cost = round(act.est_cost * scale, 2)

        # Ensure at least one free item if budget is near zero
        if budget_per_day < 5 and activities:
            activities[-1].est_cost = 0.0
        return activities

    def _label_city(self, value: str) -> str:
        if value in self._airport_to_city:
            return self._airport_to_city[value]
        return value
