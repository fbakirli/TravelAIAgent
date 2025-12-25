# models/itinerary.py
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional

@dataclass
class Activity:
    name: str
    description: str
    est_cost: float = 0.0
    link: Optional[str] = None

@dataclass
class ItineraryDay:
    date: date
    city: str
    activities: List[Activity] = field(default_factory=list)
    transport: Optional[str] = None

@dataclass
class Itinerary:
    origin: str
    destinations: List[str]
    days: List[ItineraryDay]

    def __str__(self) -> str:
        lines: List[str] = []
        for i, d in enumerate(self.days, start=1):
            lines.append(f"Day {i} ({d.date}) — {d.city}")
            if d.transport:
                lines.append(f"  Transport: {d.transport}")
            if not d.activities:
                lines.append("  • Free time / explore locally")
            else:
                for a in d.activities:
                    cost = f" (${a.est_cost:.0f})" if a.est_cost else ""
                    lines.append(f"  • {a.name}{cost}")
                    if a.link:
                        lines.append(f"    Link: [Open]({a.link})")
                    desc = self._shorten(a.description, a.name)
                    if desc:
                        lines.append(f"    {desc}")
            lines.append("")
        return "\n".join(lines).rstrip()

    def _shorten(self, text: str, name: str, limit: int = 180) -> str:
        if not text:
            return ""
        clean = " ".join(str(text).split())
        # avoid repeating the name as description
        if clean.lower() == str(name or "").lower():
            return ""
        if len(clean) <= limit:
            return clean
        return clean[: limit - 3].rstrip() + "..."
