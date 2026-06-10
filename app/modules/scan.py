from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime

from app.models.scan import ScanRecord, ScanLocation
from app.models.baggage import BaggageStatus
from app.storage.memory import storage
from app.modules.anomaly import run_all_checks, detect_damaged
from app.modules.notification import send_status_notification

router = APIRouter(prefix="/scans", tags=["scans"])

LOCATION_STATUS_MAP = {
    "checkin_counter": BaggageStatus.CHECKED_IN,
    "security_scanner": "security_passed",
    "sorting_machine": "sorted",
    "loading_gate": "loaded",
    "unloading_gate": "unloaded",
    "customs": "customs_passed",
    "carousel_entry": "carousel_entered",
    "carousel_exit": "claimed",
    "exit_gate": "departed",
}


def _update_baggage_status_from_scan(scan: ScanRecord):
    status = LOCATION_STATUS_MAP.get(scan.location)
    if status:
        storage.update_baggage_status(scan.tag_id, status)


def _should_skip_customs(tag_id: str) -> bool:
    baggage = storage.get_baggage(tag_id)
    if not baggage:
        return True
    return not baggage.is_international


@router.post("/", response_model=ScanRecord)
async def create_scan(scan_in: dict):
    tag_id = scan_in.get("tag_id")
    if not tag_id:
        raise HTTPException(status_code=400, detail="tag_id is required")

    baggage = storage.get_baggage(tag_id)
    if not baggage:
        raise HTTPException(status_code=404, detail="Baggage not found")

    location = scan_in.get("location")
    if not location:
        raise HTTPException(status_code=400, detail="location is required")

    if location == "customs" and _should_skip_customs(tag_id):
        raise HTTPException(
            status_code=400,
            detail="Domestic flights skip customs inspection"
        )

    scan = ScanRecord(
        tag_id=tag_id,
        location=location,
        device_id=scan_in.get("device_id", "UNKNOWN"),
        flight_number=scan_in.get("flight_number") or baggage.flight_number,
        extra=scan_in.get("extra", {}),
    )

    if scan_in.get("timestamp"):
        scan.timestamp = datetime.fromisoformat(scan_in["timestamp"])

    storage.add_scan(scan)
    _update_baggage_status_from_scan(scan)

    status = LOCATION_STATUS_MAP.get(location)
    if status:
        await send_status_notification(tag_id, status)

    anomalies = await run_all_checks(
        tag_id,
        current_flight=scan.flight_number,
        current_time=scan.timestamp,
    )

    return scan


@router.get("/tag/{tag_id}", response_model=List[ScanRecord])
async def get_scans_by_tag(tag_id: str):
    scans = storage.get_scans_by_tag(tag_id)
    if not scans:
        raise HTTPException(status_code=404, detail="No scans found for this tag")
    return scans


@router.get("/flight/{flight_number}", response_model=List[ScanRecord])
async def get_scans_by_flight(flight_number: str):
    return storage.get_scans_by_flight(flight_number)


@router.get("/latest/{tag_id}", response_model=ScanRecord)
async def get_latest_scan(tag_id: str):
    scan = storage.get_latest_scan(tag_id)
    if not scan:
        raise HTTPException(status_code=404, detail="No scans found for this tag")
    return scan


@router.post("/damage-report")
async def report_damage(tag_id: str, description: str, location: str = "unknown"):
    baggage = storage.get_baggage(tag_id)
    if not baggage:
        raise HTTPException(status_code=404, detail="Baggage not found")

    anomaly = detect_damaged(tag_id, {"description": description, "location": location})

    return {
        "tag_id": tag_id,
        "damage_reported": True,
        "anomaly_id": anomaly.anomaly_id if anomaly else None,
        "description": description,
        "location": location,
    }


@router.get("/anomalies/tag/{tag_id}")
async def get_anomalies_by_tag(tag_id: str):
    return storage.get_anomalies_by_tag(tag_id)


@router.get("/anomalies/flight/{flight_number}")
async def get_anomalies_by_flight(flight_number: str):
    return storage.get_anomalies_by_flight(flight_number)


@router.get("/anomalies/type/{anomaly_type}")
async def get_anomalies_by_type(anomaly_type: str):
    return storage.get_anomalies_by_type(anomaly_type)


@router.post("/simulate-batch")
async def simulate_batch_scans(scans: List[dict]):
    results = []
    for scan_data in scans:
        try:
            result = await create_scan(scan_data)
            results.append({"success": True, "scan": result})
        except Exception as e:
            results.append({"success": False, "error": str(e), "data": scan_data})

    return {
        "total": len(scans),
        "success_count": sum(1 for r in results if r["success"]),
        "fail_count": sum(1 for r in results if not r["success"]),
        "results": results,
    }
