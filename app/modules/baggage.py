from fastapi import APIRouter, HTTPException
from typing import List
import random

from app.models.baggage import Baggage, BaggageStatus
from app.storage.memory import storage
from app.modules.notification import send_status_notification

router = APIRouter(prefix="/baggage", tags=["baggage"])


def _generate_tag_id() -> str:
    return ''.join([str(random.randint(0, 9)) for _ in range(10)])


@router.post("/", response_model=Baggage)
async def create_baggage(baggage_in: dict):
    required_fields = ["passenger_name", "ticket_number", "flight_number", "weight_kg", "destination", "origin"]
    missing = [f for f in required_fields if f not in baggage_in or baggage_in[f] is None]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required fields: {', '.join(missing)}")

    raw_tag_id = baggage_in.get("tag_id")
    if raw_tag_id:
        if not isinstance(raw_tag_id, str) or len(raw_tag_id) != 10 or not raw_tag_id.isdigit():
            raise HTTPException(status_code=400, detail="tag_id must be a 10-digit numeric string")
        tag_id = raw_tag_id
    else:
        tag_id = _generate_tag_id()

    if storage.get_baggage(tag_id):
        raise HTTPException(status_code=409, detail=f"Tag ID {tag_id} already exists")

    flight = storage.get_flight(baggage_in.get("flight_number", ""))
    is_international = flight.is_international if flight else baggage_in.get("is_international", False)

    if not isinstance(baggage_in["weight_kg"], (int, float)) or baggage_in["weight_kg"] <= 0:
        raise HTTPException(status_code=400, detail="weight_kg must be a positive number")

    try:
        baggage = Baggage(
            tag_id=tag_id,
            passenger_name=str(baggage_in["passenger_name"]).strip(),
            ticket_number=str(baggage_in["ticket_number"]).strip(),
            flight_number=str(baggage_in["flight_number"]).strip(),
            weight_kg=float(baggage_in["weight_kg"]),
            declared_value=baggage_in.get("declared_value"),
            destination=str(baggage_in["destination"]).strip(),
            origin=str(baggage_in["origin"]).strip(),
            language=baggage_in.get("language", "zh"),
            is_international=is_international,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid baggage data: {str(e)}")

    result = storage.add_baggage(baggage)
    await send_status_notification(tag_id, BaggageStatus.CHECKED_IN)
    return result


@router.get("/{tag_id}", response_model=Baggage)
async def get_baggage(tag_id: str):
    baggage = storage.get_baggage(tag_id)
    if not baggage:
        raise HTTPException(status_code=404, detail="Baggage not found")
    return baggage


@router.get("/ticket/{ticket_number}", response_model=Baggage)
async def get_baggage_by_ticket(ticket_number: str):
    baggage = storage.get_baggage_by_ticket(ticket_number)
    if not baggage:
        raise HTTPException(status_code=404, detail="Baggage not found")
    return baggage


@router.get("/flight/{flight_number}", response_model=List[Baggage])
async def get_baggages_by_flight(flight_number: str):
    return storage.get_baggages_by_flight(flight_number)


@router.put("/{tag_id}/status", response_model=Baggage)
async def update_baggage_status(tag_id: str, status: str):
    baggage = storage.update_baggage_status(tag_id, status)
    if not baggage:
        raise HTTPException(status_code=404, detail="Baggage not found")
    await send_status_notification(tag_id, status)
    return baggage


@router.post("/{tag_id}/reassign-flight", response_model=Baggage)
async def reassign_baggage_flight(tag_id: str, new_flight_number: str):
    baggage = storage.reassign_baggage_flight(tag_id, new_flight_number)
    if not baggage:
        raise HTTPException(status_code=404, detail="Baggage not found")

    flight = storage.get_flight(new_flight_number)
    if flight:
        baggage.destination = flight.destination
        baggage.is_international = flight.is_international

    return baggage
