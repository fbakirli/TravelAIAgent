# models/budget.py
from __future__ import annotations
from dataclasses import dataclass

@dataclass
class BudgetBreakdown:
    flights: float = 0.0
    hotels: float = 0.0
    activities: float = 0.0

    @property
    def total(self) -> float:
        return float(self.flights + self.hotels + self.activities)

    def remaining(self, budget: float) -> float:
        return float(budget - self.total)
