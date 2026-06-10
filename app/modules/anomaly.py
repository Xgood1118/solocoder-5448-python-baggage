from datetime import datetime, timedelta
from typing import Optional

from app.models.anomaly import AnomalyRecord, AnomalyType, AnomalySeverity
from app.models.baggage import BaggageStatus
from app.models.lost import LostRecord, LostStatus
from app.storage.memory import storage
from app.config import settings
from app.utils import generate_id
from app.modules.notification import send_anomaly_notification


def detect_misrouted(tag_id: str, current_flight_number: str) -> Optional[AnomalyRecord]:
    baggage = storage.get_baggage(tag_id)
    if not baggage:
        return None

    if baggage.flight_number != current_flight_number:
        anomalies = storage.get_anomalies_by_tag(tag_id)
        for a in anomalies:
            if a.anomaly_type == AnomalyType.MISROUTED and not a.resolved:
                return None

        anomaly = AnomalyRecord(
            anomaly_id=generate_id("MIS"),
            tag_id=tag_id,
            flight_number=current_flight_number,
            anomaly_type=AnomalyType.MISROUTED,
            severity=AnomalySeverity.HIGH,
            description=f"行李错运：应搭乘 {baggage.flight_number}，实际搭乘 {current_flight_number}",
            correct_flight_number=baggage.flight_number,
        )
        storage.add_anomaly(anomaly)
        storage.update_baggage_status(tag_id, BaggageStatus.MISROUTED)

        return anomaly

    return None


def detect_damaged(tag_id: str, damage_info: dict) -> Optional[AnomalyRecord]:
    baggage = storage.get_baggage(tag_id)
    if not baggage:
        return None

    anomaly = AnomalyRecord(
        anomaly_id=generate_id("DMG"),
        tag_id=tag_id,
        flight_number=baggage.flight_number,
        anomaly_type=AnomalyType.DAMAGED,
        severity=AnomalySeverity.MEDIUM,
        description=f"行李损坏：{damage_info.get('description', '未描述')}",
        damage_description=damage_info.get("description"),
    )
    storage.add_anomaly(anomaly)
    storage.update_baggage_status(tag_id, BaggageStatus.DAMAGED)

    return anomaly


def _is_in_flight_phase(tag_id: str) -> bool:
    scans = storage.get_scans_by_tag(tag_id)
    if not scans:
        return False

    locations = [s.location for s in scans]

    if "loading_gate" in locations:
        if "unloading_gate" in locations:
            return False
        return True

    return False


def detect_lost(tag_id: str, current_time: Optional[datetime] = None) -> Optional[AnomalyRecord]:
    if current_time is None:
        current_time = datetime.utcnow()

    baggage = storage.get_baggage(tag_id)
    if not baggage:
        return None

    if baggage.status in [BaggageStatus.CLAIMED, BaggageStatus.DEPARTED, BaggageStatus.LOST]:
        return None

    anomalies = storage.get_anomalies_by_tag(tag_id)
    for a in anomalies:
        if a.anomaly_type == AnomalyType.LOST and not a.resolved:
            return None

    if _is_in_flight_phase(tag_id):
        return None

    latest_scan = storage.get_latest_scan(tag_id)
    if not latest_scan:
        return None

    time_since_last_scan = current_time - latest_scan.timestamp
    threshold = timedelta(minutes=settings.LOST_THRESHOLD_MINUTES)

    if time_since_last_scan > threshold:
        anomaly = AnomalyRecord(
            anomaly_id=generate_id("LST"),
            tag_id=tag_id,
            flight_number=baggage.flight_number,
            anomaly_type=AnomalyType.LOST,
            severity=AnomalySeverity.CRITICAL,
            description=f"行李丢失：最后一次扫描在 {latest_scan.location}，已超过 {settings.LOST_THRESHOLD_MINUTES} 分钟无更新",
        )
        storage.add_anomaly(anomaly)
        storage.update_baggage_status(tag_id, BaggageStatus.LOST)

        lost_record = LostRecord(
            lost_id=generate_id("LR"),
            tag_id=tag_id,
            flight_number=baggage.flight_number,
            passenger_name=baggage.passenger_name,
            ticket_number=baggage.ticket_number,
            last_known_location=latest_scan.location,
            last_seen_at=latest_scan.timestamp,
            status=LostStatus.INVESTIGATING,
        )
        storage.add_lost_record(lost_record)

        return anomaly

    return None


def detect_delayed(tag_id: str) -> Optional[AnomalyRecord]:
    baggage = storage.get_baggage(tag_id)
    if not baggage:
        return None

    anomalies = storage.get_anomalies_by_tag(tag_id)
    for a in anomalies:
        if a.anomaly_type == AnomalyType.DELAYED and not a.resolved:
            return None

    flight = storage.get_flight(baggage.flight_number)
    if not flight:
        return None

    scans = storage.get_scans_by_tag(tag_id)
    if not scans:
        return None

    loading_scan = None
    unloading_scan = None

    for scan in scans:
        if scan.location == "loading_gate":
            loading_scan = scan
        if scan.location == "unloading_gate":
            unloading_scan = scan

    if not unloading_scan or not flight.actual_arrival:
        return None

    delay_threshold_hours = settings.DELAY_INTL_HOURS if baggage.is_international else settings.DELAY_DOMESTIC_HOURS
    expected_arrival = flight.actual_arrival + timedelta(hours=1)

    if unloading_scan.timestamp > expected_arrival:
        delay_hours = (unloading_scan.timestamp - flight.actual_arrival).total_seconds() / 3600

        is_compensated = delay_hours >= delay_threshold_hours
        compensation = 0.0

        if is_compensated:
            if baggage.declared_value:
                compensation = min(baggage.declared_value, settings.MONTREAL_CONVENTION_LIMIT_SDR * 1.37)
            else:
                compensation = min(baggage.weight_kg * 30, settings.MONTREAL_CONVENTION_LIMIT_SDR * 1.37)

        anomaly = AnomalyRecord(
            anomaly_id=generate_id("DLY"),
            tag_id=tag_id,
            flight_number=baggage.flight_number,
            anomaly_type=AnomalyType.DELAYED,
            severity=AnomalySeverity.MEDIUM,
            description=f"行李延误：航班落地 {flight.actual_arrival.isoformat()}，卸机时间 {unloading_scan.timestamp.isoformat()}，延误 {delay_hours:.2f} 小时",
            delay_hours=delay_hours,
            compensation_amount=compensation if is_compensated else 0,
        )
        storage.add_anomaly(anomaly)
        storage.update_baggage_status(tag_id, BaggageStatus.DELAYED)

        return anomaly

    return None


async def run_all_checks(tag_id: str, current_flight: str = None, current_time: datetime = None):
    results = {}

    if current_flight:
        misrouted = detect_misrouted(tag_id, current_flight)
        if misrouted:
            results["misrouted"] = misrouted
            await send_anomaly_notification(tag_id, misrouted)

    lost = detect_lost(tag_id, current_time)
    if lost:
        results["lost"] = lost
        await send_anomaly_notification(tag_id, lost)

    delayed = detect_delayed(tag_id)
    if delayed:
        results["delayed"] = delayed
        await send_anomaly_notification(tag_id, delayed)

    return results
