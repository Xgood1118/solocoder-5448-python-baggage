from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ClaimStatus(str):
    PENDING = "pending"
    VERIFIED = "verified"
    CLAIMED = "claimed"
    REJECTED = "rejected"


class ClaimRecord(BaseModel):
    claim_id: str
    tag_id: str
    ticket_number: str
    passenger_name: str
    claimant_name: str
    tag_last4: str
    status: str = ClaimStatus.PENDING
    verified: bool = False
    claimed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    notes: Optional[str] = None
