# utils/money.py
from __future__ import annotations

def clamp_non_negative(x: float) -> float:
    return max(0.0, float(x))

def safe_div(a: float, b: float) -> float:
    if b == 0:
        return 0.0
    return a / b
