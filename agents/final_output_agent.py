# agents/final_output_agent.py
from __future__ import annotations
from typing import Dict, List, Optional

from models.budget import BudgetBreakdown
from models.flight import FlightOption
from models.hotel import HotelOption
from models.itinerary import Itinerary
from models.preferences import TravelPreferences

class FinalOutputAgent:
    def render(
        self,
        prefs: TravelPreferences,
        flights: List[FlightOption],
        hotels: Dict[str, HotelOption],
        itinerary: Itinerary,
        budget: BudgetBreakdown,
        travel_tips: Optional[List[str]] = None,
        travel_fares: Optional[Dict[str, float]] = None,
    ) -> str:
        lines: List[str] = []

        lines.append("✅ Travel Package")
        lines.append("")
        lines.append("### Preferences")
        route = " → ".join(itinerary.destinations) if getattr(itinerary, "destinations", None) else (
            " → ".join(prefs.destinations) if prefs.destinations else "—"
        )
        lines.append(f"- **Origin:** {prefs.origin_city}")
        lines.append(f"- **Route:** {route}")
        lines.append(f"- **Dates:** {prefs.start_date} → {prefs.end_date} ({prefs.num_days} days)")
        lines.append(f"- **Budget:** ${prefs.total_budget:.0f}")
        if travel_fares:
            fare_bits = [f"{city}: ~{fare}" for city, fare in travel_fares.items()]
            if fare_bits:
                lines.append(f"- **Transit fares:** {', '.join(fare_bits)}")
        lines.append("")

        lines.append("### Flights")
        if not flights:
            lines.append("- _No flights found._")
        else:
            for idx, f in enumerate(flights, start=1):
                link = f" | [Link]({f.booking_link})" if f.booking_link else ""
                lines.append(
                    f"{idx}) **{f.origin} → {f.destination}** | {f.airline} | {f.depart_date} {f.departure_time}–{f.arrival_time} | ${f.price:.0f}{link}"
                )
        lines.append("")

        lines.append("### Hotels")
        if not hotels:
            lines.append("- _No hotels found._")
        else:
            for city, h in hotels.items():
                link = f" | [Link]({h.link})" if h.link else ""
                lines.append(
                    f"- **{city}:** {h.name} | {h.check_in} → {h.check_out} | ${h.price:.0f}/night | ⭐ {h.rating} ({h.reviews} reviews){link}"
                )
        lines.append("")

        lines.append("### Itinerary")
        itinerary_text = str(itinerary)
        if itinerary_text:
            lines.append(itinerary_text)
        else:
            lines.append("- _No daily plan available._")
        lines.append("")

        lines.append("### Budget")
        lines.append(f"- Flights: ${budget.flights:.0f}")
        lines.append(f"- Hotels: ${budget.hotels:.0f}")
        lines.append(f"- Activities: ${budget.activities:.0f}")
        lines.append(f"- **Total:** ${budget.total:.0f}")
        remaining = budget.remaining(prefs.total_budget)
        lines.append(f"- **Remaining:** ${remaining:.0f}")

        if remaining < 0:
            lines.append("")
            lines.append("⚠️ Over budget. Consider cheaper dates, fewer cities, or lower hotel tier.")

        if travel_tips:
            lines.append("")
            lines.append("Travel tips")
            for tip in travel_tips[:5]:
                lines.append(f"- {tip}")

        return "\n".join(lines)
