# clients/attractions_client.py
from __future__ import annotations
from typing import List, Optional, Dict

from clients.serpapi_client import SerpApiClient


class AttractionsClient:
    """
    Fetches attractions via SerpApi Google Local (real data only).
    Returns a list of dicts with name/link so downstream can show URLs.
    """

    def __init__(self, serpapi: Optional[SerpApiClient] = None):
        self.serpapi = serpapi or SerpApiClient()

    def top_attractions(self, city: str, limit: int = 10) -> List[Dict[str, str]]:
        if not self.serpapi.enabled():
            return []

        try:
            data = self.serpapi.get(
                engine="google_local",
                params={
                    "q": f"top attractions in {city}",
                    "location": city,
                    "hl": "en",
                    "num": limit,
                },
            )
            items = []
            for r in data.get("local_results", []):
                name = r.get("title") or r.get("name")
                link = r.get("link")
                if name:
                    items.append({"name": name, "link": link or ""})
            return items[:limit]
        except Exception as e:
            print(f"⚠️ SerpApi attractions fallback for {city}: {e}")
            return []
