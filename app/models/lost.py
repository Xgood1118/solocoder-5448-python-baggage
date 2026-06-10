from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class LostStatus(str):
    REPORTED = "reported"
    INVESTIGATING = "investigating"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    FOUND = "found"
    CLOSED = "closed"


class LostRecord(BaseModel):
    lost_id: str
    tag_id: str
    flight_number: str
    passenger_name: str
    ticket_number: str
    reported_at: datetime = Field(default_factory=datetime.utcnow)
    found_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    status: str = LostStatus.REPORTED
    last_known_location: Optional[str] = None
    last_seen_at: Optional[datetime] = None
    delivery_address: Optional[str] = None
    compensation_amount: Optional[float] = None
    notes: Optional[str] = None
