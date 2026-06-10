from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class AnomalyType(str):
    MISROUTED = "misrouted"
    DAMAGED = "damaged"
    LOST = "lost"
    DELAYED = "delayed"


class AnomalySeverity(str):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AnomalyRecord(BaseModel):
    anomaly_id: str
    tag_id: str
    flight_number: str
    anomaly_type: str
    severity: str = AnomalySeverity.MEDIUM
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    resolved: bool = False
    description: str
    correct_flight_number: Optional[str] = None
    damage_description: Optional[str] = None
    delay_hours: Optional[float] = None
    compensation_amount: Optional[float] = None
    notes: Optional[str] = None
