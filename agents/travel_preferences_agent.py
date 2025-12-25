# agents/travel_preferences_agent.py
from __future__ import annotations
from dataclasses import asdict
from datetime import date, timedelta
from typing import Any, Dict, Optional

from models.preferences import TravelPreferences
from utils.date_parser import parse_date
from utils.money import clamp_non_negative

class TravelPreferencesAgent:
    """
    Validates/normalizes user input into TravelPreferences.
    Works with either a raw dict OR an already built TravelPreferences.
    """

    def normalize(self, raw: Any) -> TravelPreferences:
        if isinstance(raw, TravelPreferences):
            prefs = raw
        elif isinstance(raw, dict):
            prefs = self._from_dict(raw)
        else:
            raise TypeError("TravelPreferencesAgent.normalize expects TravelPreferences or dict")

        # Defaults & fixes
        if not prefs.origin_city:
            prefs.origin_city = "GYD"  # default to Baku airport code

        if not prefs.destinations:
            prefs.destinations = ["IST"]

        prefs.num_days = int(prefs.num_days or 3)
        prefs.num_locations = int(prefs.num_locations or max(1, len(prefs.destinations)))

        prefs.total_budget = clamp_non_negative(float(prefs.total_budget or 0.0))
        if prefs.total_budget <= 0:
            prefs.total_budget = 500.0

        today = date.today()
        if prefs.start_date is None:
            prefs.start_date = today + timedelta(days=10)

        # Move past dates to the next available year so external APIs don't reject them.
        if prefs.start_date and prefs.start_date < today:
            bumped = None
            try:
                bumped = prefs.start_date.replace(year=today.year)
            except ValueError:
                bumped = None

            if bumped is None or bumped < today:
                try:
                    bumped = prefs.start_date.replace(year=today.year + 1)
                except ValueError:
                    bumped = None

            prefs.start_date = bumped or (today + timedelta(days=10))

        if prefs.end_date is None:
            prefs.end_date = prefs.start_date + timedelta(days=prefs.num_days)
        elif prefs.end_date <= prefs.start_date:
            prefs.end_date = prefs.start_date + timedelta(days=prefs.num_days)

        return prefs

    def _from_dict(self, d: Dict[str, Any]) -> TravelPreferences:
        start = d.get("start_date")
        end = d.get("end_date")

        start_date: Optional[date] = start if isinstance(start, date) else parse_date(str(start)) if start else None
        end_date: Optional[date] = end if isinstance(end, date) else parse_date(str(end)) if end else None

        return TravelPreferences(
            origin_city=str(d.get("origin_city", "")).strip(),
            destinations=list(d.get("destinations") or []),
            num_days=int(d.get("num_days") or 0),
            num_locations=int(d.get("num_locations") or 0),
            total_budget=float(d.get("total_budget") or 0.0),
            start_date=start_date,
            end_date=end_date,
        )
