from fastapi import APIRouter, HTTPException
from typing import List, Optional
from datetime import datetime

from app.models.claim import ClaimRecord, ClaimStatus
from app.storage.memory import storage
from app.utils import generate_id

router = APIRouter(prefix="/claims", tags=["claims"])


def _verify_identity(baggage, ticket_number: str, tag_last4: str) -> bool:
    if not baggage:
        return False
    if baggage.ticket_number != ticket_number:
        return False
    if baggage.tag_id[-4:] != tag_last4:
        return False
    return True


@router.post("/", response_model=ClaimRecord)
async def create_claim(claim_in: dict):
    tag_id = claim_in.get("tag_id")
    ticket_number = claim_in.get("ticket_number")
    tag_last4 = claim_in.get("tag_last4")

    if not tag_id or not ticket_number or not tag_last4:
        raise HTTPException(status_code=400, detail="tag_id, ticket_number, and tag_last4 are required")

    baggage = storage.get_baggage(tag_id)
    if not baggage:
        raise HTTPException(status_code=404, detail="Baggage not found")

    verified = _verify_identity(baggage, ticket_number, tag_last4)

    claim = ClaimRecord(
        claim_id=generate_id("CL"),
        tag_id=tag_id,
        ticket_number=ticket_number,
        passenger_name=baggage.passenger_name,
        claimant_name=claim_in.get("claimant_name", baggage.passenger_name),
        tag_last4=tag_last4,
        status=ClaimStatus.VERIFIED if verified else ClaimStatus.REJECTED,
        verified=verified,
        claimed_at=datetime.utcnow() if verified else None,
        notes=claim_in.get("notes"),
    )

    storage.add_claim(claim)

    if verified:
        storage.update_baggage_status(tag_id, "claimed")

    return claim


@router.get("/{claim_id}", response_model=ClaimRecord)
async def get_claim(claim_id: str):
    claim = storage.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim


@router.get("/tag/{tag_id}", response_model=List[ClaimRecord])
async def get_claims_by_tag(tag_id: str):
    return storage.get_claims_by_tag(tag_id)


@router.post("/verify")
async def verify_claim_identity(tag_id: str, ticket_number: str, tag_last4: str):
    baggage = storage.get_baggage(tag_id)
    if not baggage:
        raise HTTPException(status_code=404, detail="Baggage not found")

    verified = _verify_identity(baggage, ticket_number, tag_last4)

    return {
        "tag_id": tag_id,
        "verified": verified,
        "passenger_name": baggage.passenger_name,
        "flight_number": baggage.flight_number,
    }


@router.put("/{claim_id}/complete", response_model=ClaimRecord)
async def complete_claim(claim_id: str):
    claim = storage.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    if not claim.verified:
        raise HTTPException(status_code=400, detail="Claim not verified")

    updated = storage.update_claim_status(
        claim_id,
        ClaimStatus.CLAIMED,
        claimed_at=datetime.utcnow(),
    )

    return updated
