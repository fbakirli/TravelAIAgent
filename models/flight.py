# models/flight.py
from __future__ import annotations
from dataclasses import dataclass

@dataclass
class FlightOption:
    origin: str
    destination: str
    depart_date: str
    airline: str
    price: float
    departure_time: str
    arrival_time: str
    booking_link: str
