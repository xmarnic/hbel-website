from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Service:
    slug: str
    name: str
    price_cents: int
    schedule: str
    capacity: int
    bookable: bool = False
    booking_url: Optional[str] = None


SERVICES = [
    Service(
        slug="3-day-morning",
        name="3 Days a Week Morning Classes",
        price_cents=37500,
        schedule="Mon/Wed/Fri, 9:00am–11:30am",
        capacity=6,
    ),
    Service(
        slug="3-day-afternoon",
        name="3 Days a Week Afternoon Classes",
        price_cents=37500,
        schedule="Mon/Wed/Fri, 12:00pm–2:30pm",
        capacity=6,
    ),
    Service(
        slug="2-day-morning",
        name="2 Days a Week Morning Classes",
        price_cents=25000,
        schedule="Tue/Thu, 9:00am–11:30am",
        capacity=6,
    ),
    Service(
        slug="2-day-afternoon",
        name="2 Days a Week Afternoon Classes",
        price_cents=25000,
        schedule="Tue/Thu, 12:00pm–2:30pm",
        capacity=6,
    ),
]
