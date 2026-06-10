from datetime import datetime
from pydantic import BaseModel, Field


class ScanLocation(str):
    CHECKIN_COUNTER = "checkin_counter"
    SECURITY_SCANNER = "security_scanner"
    SORTING_MACHINE = "sorting_machine"
    LOADING_GATE = "loading_gate"
    UNLOADING_GATE = "unloading_gate"
    CUSTOMS = "customs"
    CAROUSEL_ENTRY = "carousel_entry"
    CAROUSEL_EXIT = "carousel_exit"
    EXIT_GATE = "exit_gate"


class ScanRecord(BaseModel):
    tag_id: str = Field(..., min_length=10, max_length=10)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    location: str
    device_id: str
    flight_number: str = None
    extra: dict = Field(default_factory=dict)
