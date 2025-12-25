from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from clients.serpapi_client import SerpApiClient


@dataclass
class TravelGuideInfo:
    tips: List[str]
    transit_fare: Optional[float]  # single-ride fare if available
    attractions: List[Dict[str, str]] = field(default_factory=list)


class TripAdvisorClient:
    """
    Reads TripAdvisor place data via SerpApi (real data only).
    Extracts traveler tips and any transit fare hints from the response.
    """

    def __init__(self, serpapi: Optional[SerpApiClient] = None):
        self.serpapi = serpapi or SerpApiClient()

    def fetch(self, city: str) -> TravelGuideInfo:
        if not self.serpapi.enabled():
            return TravelGuideInfo(tips=[], transit_fare=None, attractions=[])

        search_data = self._search_places(city)
        attractions = self._extract_attractions(search_data)

        # Step 1: search to find the GEO place_id for the city
        place_meta = self._select_city_place(search_data)
        if not place_meta:
            return TravelGuideInfo(tips=[], transit_fare=None, attractions=attractions)

        place_id = place_meta.get("place_id")
        place_q = place_meta.get("title") or city
        if not place_id:
            return TravelGuideInfo(tips=[], transit_fare=None, attractions=attractions)

        # Step 2: fetch the place by place_id to get travel_guide/ai_travel_tips
        try:
            place_data = self.serpapi.get(
                engine="tripadvisor",
                params={
                    "q": place_q,
                    "place_id": place_id,
                    "tripadvisor_domain": "www.tripadvisor.com",
                    "hl": "en",
                },
            )
        except Exception as e:
            print(f"⚠️ TripAdvisor place fetch failed for {city}: {e}")
            return TravelGuideInfo(tips=[], transit_fare=None, attractions=attractions)

        if not place_data:
            return TravelGuideInfo(tips=[], transit_fare=None, attractions=attractions)

        payload = place_data.get("place_result") or place_data
        tips = self._extract_tips(payload)
        fare = self._extract_transit_fare(payload)
        return TravelGuideInfo(tips=tips, transit_fare=fare, attractions=attractions)

    def _search_places(self, city: str) -> Dict[str, Any]:
        try:
            return self.serpapi.get(
                engine="tripadvisor",
                params={
                    "q": city,
                    "tripadvisor_domain": "www.tripadvisor.com",
                    "hl": "en",
                    "limit": 30,
                },
            )
        except Exception as e:
            print(f"⚠️ TripAdvisor search failed for {city}: {e}")
            return {}

    def _select_city_place(self, search_data: Dict[str, Any]) -> Optional[dict]:
        for place in search_data.get("places", []):
            if place.get("place_type") == "GEO" and place.get("place_id"):
                return place
        # fallback: first place with place_id
        for place in search_data.get("places", []):
            if place.get("place_id"):
                return place
        return None

    def _extract_attractions(self, data: Dict[str, Any], limit: int = 30) -> List[Dict[str, str]]:
        attractions: List[Dict[str, str]] = []
        places = data.get("places", []) or []
        allowed_types = {"ATTRACTION", "ATTRACTION_PRODUCT", "EATERY"}

        for place in places:
            if place.get("place_type") not in allowed_types:
                continue
            name = place.get("title")
            if not name:
                continue
            link = place.get("link") or place.get("website") or ""
            desc = place.get("description") or ""
            if not desc:
                highlighted = place.get("highlighted_review") or {}
                desc = highlighted.get("text") or ""
            desc = self._clean_text(desc)

            attractions.append(
                {
                    "name": name,
                    "link": link,
                    "description": desc,
                }
            )
            if len(attractions) >= limit:
                break

        return attractions

    def _extract_tips(self, data: dict) -> List[str]:
        tips: List[str] = []

        # ai_travel_tips → answer.sections[].snippet
        for tip in data.get("ai_travel_tips", []):
            answer = tip.get("answer") or {}
            sections = answer.get("sections") or []
            for sec in sections:
                snippet = sec.get("snippet")
                if snippet:
                    tips.append(snippet.strip())

        # travel_guide.travelers_tips[].tip
        travel_guide = data.get("travel_guide") or {}
        for t in travel_guide.get("travelers_tips", []):
            txt = t.get("tip")
            if txt:
                tips.append(txt.strip())

        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for t in tips:
            if t not in seen:
                deduped.append(t)
                seen.add(t)
        return deduped

    def _extract_transit_fare(self, data: dict) -> Optional[float]:
        candidates: List[str] = []

        # ai_travel_tips sections with "Cost" keywords
        for tip in data.get("ai_travel_tips", []):
            answer = tip.get("answer") or {}
            for sec in answer.get("sections") or []:
                title = (sec.get("title") or "").lower()
                snippet = sec.get("snippet") or ""
                if "cost" in title or "fare" in title or "ticket" in title:
                    candidates.append(snippet)

        # travel_guide practical_info
        travel_guide = data.get("travel_guide") or {}
        for item in travel_guide.get("practical_info", []):
            question = (item.get("question") or "").lower()
            if "best way" in question or "transport" in question or "get there" in question:
                answer = item.get("answer") or {}
                for sec in answer.get("sections") or []:
                    snippet = sec.get("snippet") or ""
                    candidates.append(snippet)

        fare = self._first_currency_number(candidates)
        return fare

    def _first_currency_number(self, texts: List[str]) -> Optional[float]:
        pattern = re.compile(r"([€$£])?\s*([0-9]+(?:[.,][0-9]+)?)")
        for txt in texts:
            match = pattern.search(txt)
            if match:
                num_str = match.group(2).replace(",", ".")
                try:
                    return float(num_str)
                except ValueError:
                    continue
        return None

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        # Collapse whitespace/newlines for cleaner itinerary display.
        return " ".join(text.split())
