# models/hotel.py
from __future__ import annotations
from dataclasses import dataclass

@dataclass
class HotelOption:
    name: str
    location: str
    check_in: str
    check_out: str
    # per-night price; total can be computed by nights * price
    price: float
    rating: float
    reviews: int
    link: str
