# models/preferences.py
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import List, Optional

@dataclass
class TravelPreferences:
    origin_city: str
    destinations: List[str]
    num_days: int
    num_locations: int
    total_budget: float
    start_date: Optional[date] = None
    end_date: Optional[date] = None
