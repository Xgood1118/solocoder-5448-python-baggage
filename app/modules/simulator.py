from fastapi import APIRouter, HTTPException, Body
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
import random
import asyncio

from app.storage.memory import storage
from app.modules.baggage import _generate_tag_id
from app.models.baggage import Baggage
from app.models.flight import Flight, FlightStatus
from app.models.scan import ScanLocation

router = APIRouter(prefix="/simulator", tags=["simulator"])


def _generate_flight_number() -> str:
    airline_codes = ["CA", "MU", "CZ", "HU", "CA", "3U", "ZH"]
    return f"{random.choice(airline_codes)}{random.randint(1000, 9999)}"


@router.post("/seed-flights")
async def seed_flights(count: int = 5, domestic_ratio: float = 0.6):
    cities_domestic = ["北京PEK", "上海PVG", "广州CAN", "深圳SZX", "成都CTU", "杭州HGH", "西安XIY", "重庆CKG"]
    cities_intl = ["首尔ICN", "东京NRT", "大阪KIX", "曼谷BKK", "新加坡SIN", "洛杉矶LAX", "纽约JFK", "伦敦LHR", "巴黎CDG", "法兰克福FRA"]

    created = []
    for i in range(count):
        flight_number = _generate_flight_number()
        is_intl = random.random() > domestic_ratio

        if is_intl:
            origin = random.choice(cities_domestic)
            destination = random.choice(cities_intl)
        else:
            origin, destination = random.sample(cities_domestic, 2)

        now = datetime.utcnow()
        dep_time = now + timedelta(hours=random.randint(1, 48))
        duration_hours = random.randint(1, 12) if is_intl else random.randint(1, 4)
        arr_time = dep_time + timedelta(hours=duration_hours)

        flight = Flight(
            flight_number=flight_number,
            origin=origin,
            destination=destination,
            scheduled_departure=dep_time,
            scheduled_arrival=arr_time,
            is_international=is_intl,
            status=FlightStatus.SCHEDULED,
        )
        storage.add_flight(flight)
        created.append(flight)

    return {
        "created_count": len(created),
        "flights": created,
    }


@router.post("/seed-baggage")
async def seed_baggage(
    flight_number: Optional[str] = None,
    count: int = 50,
    body: Optional[dict] = Body(default=None),
):
    if body:
        flight_number = body.get("flight_number", flight_number)
        count = body.get("count", count)

    if not flight_number:
        raise HTTPException(status_code=400, detail="flight_number is required")

    flight = storage.get_flight(flight_number)
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")

    first_names = ["张伟", "王芳", "李娜", "刘洋", "陈静", "王强", "李磊", "张敏", "John", "Mary", "David", "Sarah", "Michael", "Emma", "Taro", "Hanako", "Minho", "Soo-jin"]
    last_names = ["", "", "", "", "", "", "", "Smith", "Johnson", "Williams", "Brown", "Davis", "", "", "Yamada", "Tanaka", "Kim", "Park"]

    languages = ["zh", "zh", "zh", "zh", "en", "ja", "ko"]

    created = []
    for i in range(count):
        tag_id = _generate_tag_id()
        first = random.choice(first_names)
        last = random.choice(last_names)
        name = f"{last}{first}" if last and first[0] in '张王李刘陈' else f"{first} {last}"

        baggage = Baggage(
            tag_id=tag_id,
            passenger_name=name,
            ticket_number=f"TKT{random.randint(10000000000, 99999999999)}",
            flight_number=flight_number,
            weight_kg=round(random.uniform(5, 32), 1),
            declared_value=round(random.uniform(500, 5000), 2) if random.random() > 0.7 else None,
            destination=flight.destination,
            origin=flight.origin,
            language=random.choice(languages),
            is_international=flight.is_international,
        )
        storage.add_baggage(baggage)
        created.append(baggage)

    return {
        "flight_number": flight_number,
        "created_count": len(created),
    }


@router.post("/simulate-full-journey")
async def simulate_full_journey(tag_id: str, speed_factor: float = 1.0):
    baggage = storage.get_baggage(tag_id)
    if not baggage:
        raise HTTPException(status_code=404, detail="Baggage not found")

    locations = [
        ("checkin_counter", "CKC001"),
        ("security_scanner", "SEC001"),
        ("sorting_machine", "SRT001"),
        ("loading_gate", "LDG001"),
        ("unloading_gate", "ULG001"),
    ]

    if baggage.is_international:
        locations.append(("customs", "CUS001"))

    locations.extend([
        ("carousel_entry", "CRS001"),
        ("carousel_exit", "CRX001"),
        ("exit_gate", "EXT001"),
    ])

    base_time = datetime.utcnow()
    created_scans = []

    for i, (location, device) in enumerate(locations):
        scan_time = base_time + timedelta(minutes=i * 15 / speed_factor)

        scan_data = {
            "tag_id": tag_id,
            "location": location,
            "device_id": device,
            "timestamp": scan_time.isoformat(),
            "flight_number": baggage.flight_number,
        }

        from app.modules.scan import create_scan
        try:
            result = await create_scan(scan_data)
            created_scans.append(result)
        except Exception as e:
            created_scans.append({"error": str(e), "location": location})

    return {
        "tag_id": tag_id,
        "scans_created": len(created_scans),
        "scans": created_scans,
    }


@router.post("/simulate-flight-batch")
async def simulate_flight_batch(flight_number: str):
    flight = storage.get_flight(flight_number)
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")

    baggages = storage.get_baggages_by_flight(flight_number)
    results = []

    for baggage in baggages[:20]:
        try:
            result = await simulate_full_journey(baggage.tag_id, speed_factor=2.0)
            results.append({"tag_id": baggage.tag_id, "success": True})
        except Exception as e:
            results.append({"tag_id": baggage.tag_id, "success": False, "error": str(e)})

    return {
        "flight_number": flight_number,
        "total": len(results),
        "results": results,
    }


@router.post("/simulate-misroute")
async def simulate_misroute(tag_id: str, wrong_flight: str):
    baggage = storage.get_baggage(tag_id)
    if not baggage:
        raise HTTPException(status_code=404, detail="Baggage not found")

    wrong_flight_obj = storage.get_flight(wrong_flight)
    if not wrong_flight_obj:
        raise HTTPException(status_code=404, detail="Wrong flight not found")

    scan_data = {
        "tag_id": tag_id,
        "location": "loading_gate",
        "device_id": "LDG-TEST-MIS",
        "flight_number": wrong_flight,
    }

    from app.modules.scan import create_scan
    result = await create_scan(scan_data)

    return {
        "tag_id": tag_id,
        "correct_flight": baggage.flight_number,
        "wrong_flight": wrong_flight,
        "scan_result": result,
    }
