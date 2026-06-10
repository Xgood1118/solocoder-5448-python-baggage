from enum import StrEnum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class BaggageStatus(StrEnum):
    CHECKED_IN = "checked_in"
    SECURITY_PASSED = "security_passed"
    SORTED = "sorted"
    LOADED = "loaded"
    IN_FLIGHT = "in_flight"
    UNLOADED = "unloaded"
    CUSTOMS_PASSED = "customs_passed"
    CAROUSEL_ENTERED = "carousel_entered"
    CLAIMED = "claimed"
    DEPARTED = "departed"
    LOST = "lost"
    MISROUTED = "misrouted"
    DAMAGED = "damaged"
    DELAYED = "delayed"


class Language(StrEnum):
    ZH = "zh"
    EN = "en"
    JA = "ja"
    KO = "ko"


class Baggage(BaseModel):
    tag_id: str = Field(..., min_length=10, max_length=10, description="10位RFID标签号")
    passenger_name: str
    ticket_number: str
    flight_number: str
    weight_kg: float
    declared_value: Optional[float] = None
    destination: str
    origin: str
    language: str = Language.ZH
    status: str = BaggageStatus.CHECKED_IN
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_international: bool = False
