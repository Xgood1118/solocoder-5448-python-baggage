from fastapi import APIRouter, HTTPException
from typing import Optional
from collections import defaultdict
from datetime import datetime

from app.storage.memory import storage
from app.models.anomaly import AnomalyType

router = APIRouter(prefix="/statistics", tags=["statistics"])


@router.get("/overview")
async def get_overview():
    return {
        "total_baggage": storage.stats_baggage_count(),
        "total_flights": storage.stats_flight_count(),
        "total_scans": storage.stats_scan_count(),
        "total_anomalies": len(storage._anomalies),
        "total_lost": len(storage._lost_records),
        "total_claims": len(storage._claims),
    }


@router.get("/flight/{flight_number}")
async def get_flight_statistics(flight_number: str):
    flight = storage.get_flight(flight_number)
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")

    baggages = storage.get_baggages_by_flight(flight_number)
    total_baggage = len(baggages)

    anomalies = storage.get_anomalies_by_flight(flight_number)

    misrouted_count = sum(1 for a in anomalies if a.anomaly_type == AnomalyType.MISROUTED)
    damaged_count = sum(1 for a in anomalies if a.anomaly_type == AnomalyType.DAMAGED)
    lost_count = sum(1 for a in anomalies if a.anomaly_type == AnomalyType.LOST)
    delayed_count = sum(1 for a in anomalies if a.anomaly_type == AnomalyType.DELAYED)
    resolved_count = sum(1 for a in anomalies if a.resolved)

    def safe_rate(numerator, denominator):
        if denominator == 0:
            return 0.0
        return round(numerator / denominator * 100, 2)

    return {
        "flight_number": flight_number,
        "total_baggage": total_baggage,
        "misroute_rate": safe_rate(misrouted_count, total_baggage),
        "lost_rate": safe_rate(lost_count, total_baggage),
        "delay_rate": safe_rate(delayed_count, total_baggage),
        "damage_rate": safe_rate(damaged_count, total_baggage),
        "anomaly_summary": {
            "misrouted": misrouted_count,
            "damaged": damaged_count,
            "lost": lost_count,
            "delayed": delayed_count,
            "resolved": resolved_count,
            "total": len(anomalies),
        },
    }


@router.get("/monthly/{year_month}")
async def get_monthly_statistics(year_month: str):
    try:
        year, month = map(int, year_month.split("-"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid format, use YYYY-MM")

    all_baggages = list(storage._baggages.values())
    monthly_baggages = [
        b for b in all_baggages
        if b.created_at.year == year and b.created_at.month == month
    ]

    all_anomalies = list(storage._anomalies.values())
    monthly_anomalies = [
        a for a in all_anomalies
        if a.detected_at.year == year and a.detected_at.month == month
    ]

    total = len(monthly_baggages)
    misrouted = sum(1 for a in monthly_anomalies if a.anomaly_type == AnomalyType.MISROUTED)
    lost = sum(1 for a in monthly_anomalies if a.anomaly_type == AnomalyType.LOST)
    delayed = sum(1 for a in monthly_anomalies if a.anomaly_type == AnomalyType.DELAYED)
    damaged = sum(1 for a in monthly_anomalies if a.anomaly_type == AnomalyType.DAMAGED)

    flight_stats = defaultdict(lambda: {"total": 0, "misrouted": 0, "lost": 0, "delayed": 0, "damaged": 0})

    for b in monthly_baggages:
        flight_stats[b.flight_number]["total"] += 1

    for a in monthly_anomalies:
        if a.anomaly_type == AnomalyType.MISROUTED:
            flight_stats[a.flight_number]["misrouted"] += 1
        elif a.anomaly_type == AnomalyType.LOST:
            flight_stats[a.flight_number]["lost"] += 1
        elif a.anomaly_type == AnomalyType.DELAYED:
            flight_stats[a.flight_number]["delayed"] += 1
        elif a.anomaly_type == AnomalyType.DAMAGED:
            flight_stats[a.flight_number]["damaged"] += 1

    def safe_rate(n, d):
        return round(n / d * 100, 2) if d > 0 else 0.0

    flight_details = []
    for flight_num, stats in flight_stats.items():
        flight_details.append({
            "flight_number": flight_num,
            "total_baggage": stats["total"],
            "misroute_rate": safe_rate(stats["misrouted"], stats["total"]),
            "lost_rate": safe_rate(stats["lost"], stats["total"]),
            "delay_rate": safe_rate(stats["delayed"], stats["total"]),
            "damage_rate": safe_rate(stats["damaged"], stats["total"]),
        })

    return {
        "year_month": year_month,
        "total_baggage": total,
        "misroute_rate": safe_rate(misrouted, total),
        "lost_rate": safe_rate(lost, total),
        "delay_rate": safe_rate(delayed, total),
        "damage_rate": safe_rate(damaged, total),
        "anomaly_summary": {
            "misrouted": misrouted,
            "lost": lost,
            "delayed": delayed,
            "damaged": damaged,
            "total": len(monthly_anomalies),
        },
        "flight_details": flight_details,
    }


@router.get("/notifications/{tag_id}")
async def get_notification_history(tag_id: str):
    baggage = storage.get_baggage(tag_id)
    if not baggage:
        raise HTTPException(status_code=404, detail="Baggage not found")

    return {
        "tag_id": tag_id,
        "passenger_name": baggage.passenger_name,
        "language": baggage.language,
        "notifications": storage.get_notifications(tag_id),
    }
