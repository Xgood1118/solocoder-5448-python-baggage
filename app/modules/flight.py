from fastapi import APIRouter, HTTPException
from typing import List, Optional

from app.models.flight import Flight, FlightStatus
from app.storage.memory import storage

router = APIRouter(prefix="/flights", tags=["flights"])


@router.post("/", response_model=Flight)
async def create_flight(flight_in: dict):
    if storage.get_flight(flight_in["flight_number"]):
        raise HTTPException(status_code=400, detail="Flight already exists")

    flight = Flight(**flight_in)
    return storage.add_flight(flight)


@router.get("/{flight_number}", response_model=Flight)
async def get_flight(flight_number: str):
    flight = storage.get_flight(flight_number)
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    return flight


@router.get("/", response_model=List[Flight])
async def list_flights(status: Optional[str] = None):
    flights = list(storage._flights.values())
    if status:
        flights = [f for f in flights if f.status == status]
    return flights


@router.put("/{flight_number}/status", response_model=Flight)
async def update_flight_status(
    flight_number: str,
    status: str,
    actual_departure: Optional[str] = None,
    actual_arrival: Optional[str] = None,
):
    from datetime import datetime

    kwargs = {}
    if actual_departure:
        kwargs["actual_departure"] = datetime.fromisoformat(actual_departure)
    if actual_arrival:
        kwargs["actual_arrival"] = datetime.fromisoformat(actual_arrival)

    flight = storage.update_flight_status(flight_number, status, **kwargs)
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")
    return flight


@router.post("/{flight_number}/reassign-baggage")
async def reassign_all_baggage(flight_number: str, new_flight_number: str):
    old_flight = storage.get_flight(flight_number)
    new_flight = storage.get_flight(new_flight_number)

    if not old_flight:
        raise HTTPException(status_code=404, detail="Original flight not found")
    if not new_flight:
        raise HTTPException(status_code=404, detail="Target flight not found")

    baggages = storage.get_baggages_by_flight(flight_number)
    reassigned = []

    for baggage in baggages:
        updated = storage.reassign_baggage_flight(baggage.tag_id, new_flight_number)
        if updated:
            updated.destination = new_flight.destination
            updated.is_international = new_flight.is_international
            reassigned.append(updated.tag_id)

    return {
        "reassigned_count": len(reassigned),
        "reassigned_tag_ids": reassigned,
        "from_flight": flight_number,
        "to_flight": new_flight_number,
    }
