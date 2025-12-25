# clients/serpapi_client.py
from __future__ import annotations
import os
import requests
from typing import Any, Dict, Optional

class SerpApiClient:
    def __init__(self, api_key: Optional[str] = None, timeout: int = 15):
        self.api_key = api_key or os.getenv("SERPAPI_KEY")
        self.timeout = timeout

    def enabled(self) -> bool:
        return bool(self.api_key)

    def get(self, engine: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("SERPAPI_KEY is missing.")
        url = "https://serpapi.com/search"
        full = dict(params)
        full["engine"] = engine
        full["api_key"] = self.api_key
        res = requests.get(url, params=full, timeout=self.timeout)
        res.raise_for_status()
        return res.json()
