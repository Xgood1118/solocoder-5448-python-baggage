import uuid
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict

from app.models.baggage import Baggage
from app.models.scan import ScanRecord
from app.models.flight import Flight
from app.models.claim import ClaimRecord
from app.models.lost import LostRecord
from app.models.anomaly import AnomalyRecord


class MemoryStorage:
    def __init__(self):
        self._baggages: Dict[str, Baggage] = {}
        self._baggages_by_flight: Dict[str, List[str]] = defaultdict(list)
        self._baggages_by_ticket: Dict[str, str] = {}

        self._scans: Dict[str, List[ScanRecord]] = defaultdict(list)
        self._scans_by_flight: Dict[str, List[ScanRecord]] = defaultdict(list)
        self._scan_count_by_flight: Dict[str, int] = defaultdict(int)

        self._flights: Dict[str, Flight] = {}

        self._claims: Dict[str, ClaimRecord] = {}
        self._claims_by_tag: Dict[str, List[str]] = defaultdict(list)

        self._lost_records: Dict[str, LostRecord] = {}
        self._lost_by_tag: Dict[str, str] = {}
        self._lost_by_flight: Dict[str, List[str]] = defaultdict(list)

        self._anomalies: Dict[str, AnomalyRecord] = {}
        self._anomalies_by_tag: Dict[str, List[str]] = defaultdict(list)
        self._anomalies_by_flight: Dict[str, List[str]] = defaultdict(list)
        self._anomalies_by_type: Dict[str, List[str]] = defaultdict(list)

        self._notifications: Dict[str, List[dict]] = defaultdict(list)

    def add_baggage(self, baggage: Baggage) -> Baggage:
        self._baggages[baggage.tag_id] = baggage
        self._baggages_by_flight[baggage.flight_number].append(baggage.tag_id)
        self._baggages_by_ticket[baggage.ticket_number] = baggage.tag_id
        return baggage

    def get_baggage(self, tag_id: str) -> Optional[Baggage]:
        return self._baggages.get(tag_id)

    def get_baggage_by_ticket(self, ticket_number: str) -> Optional[Baggage]:
        tag_id = self._baggages_by_ticket.get(ticket_number)
        return self._baggages.get(tag_id) if tag_id else None

    def get_baggages_by_flight(self, flight_number: str) -> List[Baggage]:
        tag_ids = self._baggages_by_flight.get(flight_number, [])
        return [self._baggages[tid] for tid in tag_ids if tid in self._baggages]

    def update_baggage_status(self, tag_id: str, status: str) -> Optional[Baggage]:
        baggage = self._baggages.get(tag_id)
        if baggage:
            baggage.status = status
            return baggage
        return None

    def reassign_baggage_flight(self, tag_id: str, new_flight_number: str) -> Optional[Baggage]:
        baggage = self._baggages.get(tag_id)
        if not baggage:
            return None

        old_flight = baggage.flight_number
        if old_flight in self._baggages_by_flight and tag_id in self._baggages_by_flight[old_flight]:
            self._baggages_by_flight[old_flight].remove(tag_id)

        baggage.flight_number = new_flight_number
        self._baggages_by_flight[new_flight_number].append(tag_id)
        return baggage

    def add_scan(self, scan: ScanRecord) -> ScanRecord:
        self._scans[scan.tag_id].append(scan)
        if scan.flight_number:
            self._scans_by_flight[scan.flight_number].append(scan)
            self._scan_count_by_flight[scan.flight_number] += 1
        return scan

    def get_scans_by_tag(self, tag_id: str) -> List[ScanRecord]:
        return sorted(self._scans.get(tag_id, []), key=lambda s: s.timestamp)

    def get_scans_by_flight(self, flight_number: str) -> List[ScanRecord]:
        return sorted(self._scans_by_flight.get(flight_number, []), key=lambda s: s.timestamp)

    def get_latest_scan(self, tag_id: str) -> Optional[ScanRecord]:
        scans = self._scans.get(tag_id, [])
        return scans[-1] if scans else None

    def add_flight(self, flight: Flight) -> Flight:
        self._flights[flight.flight_number] = flight
        return flight

    def get_flight(self, flight_number: str) -> Optional[Flight]:
        return self._flights.get(flight_number)

    def update_flight_status(self, flight_number: str, status: str, **kwargs) -> Optional[Flight]:
        flight = self._flights.get(flight_number)
        if flight:
            flight.status = status
            for key, value in kwargs.items():
                if hasattr(flight, key) and value is not None:
                    setattr(flight, key, value)
            return flight
        return None

    def add_claim(self, claim: ClaimRecord) -> ClaimRecord:
        self._claims[claim.claim_id] = claim
        self._claims_by_tag[claim.tag_id].append(claim.claim_id)
        return claim

    def get_claim(self, claim_id: str) -> Optional[ClaimRecord]:
        return self._claims.get(claim_id)

    def get_claims_by_tag(self, tag_id: str) -> List[ClaimRecord]:
        claim_ids = self._claims_by_tag.get(tag_id, [])
        return [self._claims[cid] for cid in claim_ids if cid in self._claims]

    def update_claim_status(self, claim_id: str, status: str, **kwargs) -> Optional[ClaimRecord]:
        claim = self._claims.get(claim_id)
        if claim:
            claim.status = status
            for key, value in kwargs.items():
                if hasattr(claim, key) and value is not None:
                    setattr(claim, key, value)
            return claim
        return None

    def add_lost_record(self, record: LostRecord) -> LostRecord:
        self._lost_records[record.lost_id] = record
        self._lost_by_tag[record.tag_id] = record.lost_id
        self._lost_by_flight[record.flight_number].append(record.lost_id)
        return record

    def get_lost_record(self, lost_id: str) -> Optional[LostRecord]:
        return self._lost_records.get(lost_id)

    def get_lost_by_tag(self, tag_id: str) -> Optional[LostRecord]:
        lost_id = self._lost_by_tag.get(tag_id)
        return self._lost_records.get(lost_id) if lost_id else None

    def get_lost_by_flight(self, flight_number: str) -> List[LostRecord]:
        lost_ids = self._lost_by_flight.get(flight_number, [])
        return [self._lost_records[lid] for lid in lost_ids if lid in self._lost_records]

    def update_lost_record(self, lost_id: str, **kwargs) -> Optional[LostRecord]:
        record = self._lost_records.get(lost_id)
        if record:
            for key, value in kwargs.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            return record
        return None

    def add_anomaly(self, anomaly: AnomalyRecord) -> AnomalyRecord:
        self._anomalies[anomaly.anomaly_id] = anomaly
        self._anomalies_by_tag[anomaly.tag_id].append(anomaly.anomaly_id)
        self._anomalies_by_flight[anomaly.flight_number].append(anomaly.anomaly_id)
        self._anomalies_by_type[anomaly.anomaly_type].append(anomaly.anomaly_id)
        return anomaly

    def get_anomaly(self, anomaly_id: str) -> Optional[AnomalyRecord]:
        return self._anomalies.get(anomaly_id)

    def get_anomalies_by_tag(self, tag_id: str) -> List[AnomalyRecord]:
        anomaly_ids = self._anomalies_by_tag.get(tag_id, [])
        return [self._anomalies[aid] for aid in anomaly_ids if aid in self._anomalies]

    def get_anomalies_by_flight(self, flight_number: str) -> List[AnomalyRecord]:
        anomaly_ids = self._anomalies_by_flight.get(flight_number, [])
        return [self._anomalies[aid] for aid in anomaly_ids if aid in self._anomalies]

    def get_anomalies_by_type(self, anomaly_type: str) -> List[AnomalyRecord]:
        anomaly_ids = self._anomalies_by_type.get(anomaly_type, [])
        return [self._anomalies[aid] for aid in anomaly_ids if aid in self._anomalies]

    def update_anomaly(self, anomaly_id: str, **kwargs) -> Optional[AnomalyRecord]:
        anomaly = self._anomalies.get(anomaly_id)
        if anomaly:
            for key, value in kwargs.items():
                if hasattr(anomaly, key):
                    setattr(anomaly, key, value)
            return anomaly
        return None

    def add_notification(self, tag_id: str, notification: dict):
        self._notifications[tag_id].append({
            "sent_at": datetime.utcnow(),
            **notification
        })

    def get_notifications(self, tag_id: str) -> List[dict]:
        return self._notifications.get(tag_id, [])

    def stats_baggage_count(self) -> int:
        return len(self._baggages)

    def stats_flight_count(self) -> int:
        return len(self._flights)

    def stats_scan_count(self) -> int:
        return sum(len(scans) for scans in self._scans.values())


storage = MemoryStorage()
