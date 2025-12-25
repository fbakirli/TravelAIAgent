# agents/travel_agent.py
from __future__ import annotations

from dataclasses import replace

from agents.travel_preferences_agent import TravelPreferencesAgent
from agents.flight_finder_agent import FlightFinderAgent
from agents.hotel_finder_agent import HotelFinderAgent
from agents.itinerary_planner_agent import ItineraryPlannerAgent
from agents.budget_optimizer_agent import BudgetOptimizerAgent
from agents.final_output_agent import FinalOutputAgent
from clients.tripadvisor_client import TripAdvisorClient
from models.preferences import TravelPreferences
from utils.airport_codes import to_airport_code


class TravelAgent:
    """
    Orchestrator that preserves working prototypes.
    """

    def __init__(self):
        self.pref_agent = TravelPreferencesAgent()
        self.flight_agent = FlightFinderAgent()   # prototype signature: (serpapi_key=None)
        self.hotel_agent = HotelFinderAgent()     # prototype signature: (serpapi_key=None)

        self.itinerary_agent = ItineraryPlannerAgent()
        self.budget_agent = BudgetOptimizerAgent()
        self.output_agent = FinalOutputAgent()
        self.tripadvisor = TripAdvisorClient()

    def run(self, prefs: TravelPreferences) -> str:
        prefs = self.pref_agent.normalize(prefs)

        # 1) Build FLIGHT-SAFE preferences (airport codes)
        flight_prefs = replace(
            prefs,
            origin_city=to_airport_code(prefs.origin_city),
            destinations=[to_airport_code(d) for d in prefs.destinations],
        )

        # 2) Call your working prototypes
        flights_all = self.flight_agent.run(flight_prefs)

        # TripAdvisor travel guide data per destination (real tips/fare only)
        travel_guides = {dest: self.tripadvisor.fetch(dest) for dest in prefs.destinations}
        combined_tips = []
        travel_fares = {}
        for info in travel_guides.values():
            combined_tips.extend(info.tips)
        for city, info in travel_guides.items():
            if info.transit_fare is not None:
                travel_fares[city] = info.transit_fare
        # dedupe
        seen = set()
        combined_tips = [t for t in combined_tips if not (t in seen or seen.add(t))]

        # Hotels should use city names (original prefs) so Google Hotels works normally
        hotels_all = self.hotel_agent.run(prefs, flights_all)

        # 3) Itinerary + budget + output (leave as your architecture requires)
        itinerary = self.itinerary_agent.run(
            prefs,
            flights_all,
            hotels_all,
            travel_guides=travel_guides,
        )
        selected_flights, selected_hotels, budget = self.budget_agent.run(
            prefs=prefs,
            flights=flights_all,
            hotels=hotels_all,
            itinerary=itinerary,
        )

        return self.output_agent.render(
            prefs=prefs,
            flights=selected_flights,
            hotels=selected_hotels,
            itinerary=itinerary,
            budget=budget,
            travel_tips=combined_tips,
            travel_fares=travel_fares,
        )
