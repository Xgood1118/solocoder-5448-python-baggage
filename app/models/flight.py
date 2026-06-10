from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class FlightStatus(str):
    SCHEDULED = "scheduled"
    BOARDING = "boarding"
    DEPARTED = "departed"
    IN_AIR = "in_air"
    LANDED = "landed"
    CANCELLED = "cancelled"
    DIVERTED = "diverted"


class Flight(BaseModel):
    flight_number: str
    origin: str
    destination: str
    scheduled_departure: datetime
    scheduled_arrival: datetime
    actual_departure: Optional[datetime] = None
    actual_arrival: Optional[datetime] = None
    status: str = FlightStatus.SCHEDULED
    is_international: bool = False
    aircraft_registration: Optional[str] = None
    is_connecting: bool = False
    connecting_flight_number: Optional[str] = None
