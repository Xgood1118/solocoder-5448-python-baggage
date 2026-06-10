from fastapi import APIRouter, HTTPException
from typing import List, Optional
from datetime import datetime

from app.models.lost import LostRecord, LostStatus
from app.models.anomaly import AnomalyRecord, AnomalyType, AnomalySeverity
from app.storage.memory import storage
from app.utils import generate_id
from app.config import settings

router = APIRouter(prefix="/lost", tags=["lost"])


@router.get("/", response_model=List[LostRecord])
async def list_lost_records(status: Optional[str] = None, flight_number: Optional[str] = None):
    if flight_number:
        records = storage.get_lost_by_flight(flight_number)
    else:
        records = list(storage._lost_records.values())

    if status:
        records = [r for r in records if r.status == status]

    return records


@router.get("/{lost_id}", response_model=LostRecord)
async def get_lost_record(lost_id: str):
    record = storage.get_lost_record(lost_id)
    if not record:
        raise HTTPException(status_code=404, detail="Lost record not found")
    return record


@router.get("/tag/{tag_id}", response_model=LostRecord)
async def get_lost_by_tag(tag_id: str):
    record = storage.get_lost_by_tag(tag_id)
    if not record:
        raise HTTPException(status_code=404, detail="Lost record not found for this tag")
    return record


@router.post("/report", response_model=LostRecord)
async def report_lost_baggage(report_in: dict):
    tag_id = report_in.get("tag_id")
    if not tag_id:
        raise HTTPException(status_code=400, detail="tag_id is required")

    baggage = storage.get_baggage(tag_id)
    if not baggage:
        raise HTTPException(status_code=404, detail="Baggage not found")

    existing = storage.get_lost_by_tag(tag_id)
    if existing:
        return existing

    latest_scan = storage.get_latest_scan(tag_id)

    record = LostRecord(
        lost_id=generate_id("LR"),
        tag_id=tag_id,
        flight_number=baggage.flight_number,
        passenger_name=baggage.passenger_name,
        ticket_number=baggage.ticket_number,
        last_known_location=latest_scan.location if latest_scan else None,
        last_seen_at=latest_scan.timestamp if latest_scan else None,
        delivery_address=report_in.get("delivery_address"),
        notes=report_in.get("notes"),
        status=LostStatus.INVESTIGATING,
    )

    storage.add_lost_record(record)

    anomaly = AnomalyRecord(
        anomaly_id=generate_id("LST"),
        tag_id=tag_id,
        flight_number=baggage.flight_number,
        anomaly_type=AnomalyType.LOST,
        severity=AnomalySeverity.CRITICAL,
        description=report_in.get("notes", "人工上报行李丢失"),
    )
    storage.add_anomaly(anomaly)
    storage.update_baggage_status(tag_id, "lost")

    return record


@router.put("/{lost_id}/found", response_model=LostRecord)
async def mark_found(lost_id: str, location: str = "unknown"):
    record = storage.get_lost_record(lost_id)
    if not record:
        raise HTTPException(status_code=404, detail="Lost record not found")

    updated = storage.update_lost_record(
        lost_id,
        status=LostStatus.FOUND,
        found_at=datetime.utcnow(),
        notes=f"Found at: {location}",
    )

    anomalies = storage.get_anomalies_by_tag(record.tag_id)
    for anomaly in anomalies:
        if anomaly.anomaly_type == AnomalyType.LOST:
            storage.update_anomaly(anomaly.anomaly_id, resolved=True, resolved_at=datetime.utcnow())

    storage.update_baggage_status(record.tag_id, "unloaded")

    return updated


@router.put("/{lost_id}/in-transit", response_model=LostRecord)
async def mark_in_transit(lost_id: str, via_flight: Optional[str] = None):
    record = storage.get_lost_record(lost_id)
    if not record:
        raise HTTPException(status_code=404, detail="Lost record not found")

    notes = f"正在转运中"
    if via_flight:
        notes += f"，航班号：{via_flight}"
        storage.reassign_baggage_flight(record.tag_id, via_flight)

    updated = storage.update_lost_record(
        lost_id,
        status=LostStatus.IN_TRANSIT,
        notes=notes,
    )

    return updated


@router.put("/{lost_id}/delivered", response_model=LostRecord)
async def mark_delivered(lost_id: str):
    record = storage.get_lost_record(lost_id)
    if not record:
        raise HTTPException(status_code=404, detail="Lost record not found")

    baggage = storage.get_baggage(record.tag_id)
    compensation = 0.0
    if baggage:
        if baggage.declared_value:
            compensation = min(baggage.declared_value, settings.MONTREAL_CONVENTION_LIMIT_SDR * 1.37)
        else:
            compensation = min(baggage.weight_kg * 30, settings.MONTREAL_CONVENTION_LIMIT_SDR * 1.37)

    updated = storage.update_lost_record(
        lost_id,
        status=LostStatus.DELIVERED,
        delivered_at=datetime.utcnow(),
        compensation_amount=compensation,
    )

    return updated


@router.put("/{lost_id}/close", response_model=LostRecord)
async def close_lost_case(lost_id: str, notes: Optional[str] = None):
    record = storage.get_lost_record(lost_id)
    if not record:
        raise HTTPException(status_code=404, detail="Lost record not found")

    updated = storage.update_lost_record(
        lost_id,
        status=LostStatus.CLOSED,
        notes=notes,
    )

    return updated


@router.post("/misrouted/reroute")
async def reroute_misrouted_baggage(tag_id: str, correct_flight_number: str):
    baggage = storage.get_baggage(tag_id)
    if not baggage:
        raise HTTPException(status_code=404, detail="Baggage not found")

    anomalies = storage.get_anomalies_by_tag(tag_id)
    misrouted_anomaly = None
    for a in anomalies:
        if a.anomaly_type == "misrouted" and not a.resolved:
            misrouted_anomaly = a
            break

    if not misrouted_anomaly:
        raise HTTPException(status_code=400, detail="No active misrouted anomaly found")

    target_flight = storage.get_flight(correct_flight_number)
    if not target_flight:
        raise HTTPException(status_code=404, detail=f"Target flight {correct_flight_number} not found")

    storage.reassign_baggage_flight(tag_id, correct_flight_number)
    baggage.destination = target_flight.destination
    baggage.is_international = target_flight.is_international

    storage.update_anomaly(
        misrouted_anomaly.anomaly_id,
        resolved=True,
        resolved_at=datetime.utcnow(),
        correct_flight_number=correct_flight_number,
        notes=f"已重新安排至航班 {correct_flight_number}",
    )

    lost_record = LostRecord(
        lost_id=generate_id("LR"),
        tag_id=tag_id,
        flight_number=correct_flight_number,
        passenger_name=baggage.passenger_name,
        ticket_number=baggage.ticket_number,
        status=LostStatus.IN_TRANSIT,
        notes=f"错运行李转运中，原航班 {misrouted_anomaly.flight_number}，转运至 {correct_flight_number}",
    )
    storage.add_lost_record(lost_record)

    storage.update_baggage_status(tag_id, "sorted")

    return {
        "tag_id": tag_id,
        "original_flight": misrouted_anomaly.flight_number,
        "correct_flight": correct_flight_number,
        "lost_record_id": lost_record.lost_id,
    }
