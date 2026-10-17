from datetime import datetime

import pytest

from app.domain.models import (
    ActiveParking,
    AllocationStatus,
    ErrorCode,
    EventType,
    ParkingEvent,
    Spot,
    SpotType,
    VehicleType,
    Zone,
    spot_number,
)
from app.repositories.in_memory import InMemoryRepository
from app.services.parking_allocation import ParkingAllocationService

pytestmark = pytest.mark.unit

TENANT_A = "biuru-centras-a"
TENANT_B = "prekybos-centras-b"
TS = datetime(2026, 11, 10, 8, 15)


def entry(
    plate,
    vehicle_type=VehicleType.STANDARD,
    has_disability_permit=False,
    preferred_zone="A",
    tenant_id=TENANT_A,
):
    return ParkingEvent(
        tenant_id=tenant_id,
        event_type=EventType.ENTRY,
        plate=plate,
        vehicle_type=vehicle_type,
        has_disability_permit=has_disability_permit,
        preferred_zone=preferred_zone,
        timestamp=TS,
    )


def exit_event(plate, tenant_id=TENANT_A, preferred_zone="A"):
    return ParkingEvent(
        tenant_id=tenant_id,
        event_type=EventType.EXIT,
        plate=plate,
        vehicle_type=VehicleType.STANDARD,
        has_disability_permit=False,
        preferred_zone=preferred_zone,
        timestamp=TS,
    )


def test_standard_car_assigned_nearest_standard_spot():
    """1 scenarijus: LTA123 gauna A-01 (10 m), A zonoje lieka 2 laisvos vietos."""
    zones = [Zone(zone_id="A", priority=1)]
    spots = [
        Spot(spot_id="A-01", zone_id="A", spot_type=SpotType.STANDARD, distance_to_entrance=10),
        Spot(spot_id="A-02", zone_id="A", spot_type=SpotType.STANDARD, distance_to_entrance=25),
        Spot(spot_id="A-03", zone_id="A", spot_type=SpotType.STANDARD, distance_to_entrance=40),
    ]
    repo = InMemoryRepository(TENANT_A, zones, spots)
    service = ParkingAllocationService(repo)

    result = service.process_event(entry("LTA123"))

    assert result.status == AllocationStatus.ASSIGNED
    assert result.spot == "A-01"
    assert result.zone == "A"
    assert result.free_in_zone == 2


def test_standard_car_gets_zone_b_when_zone_a_has_only_ev_spot():
    """2 scenarijus: EV konfliktas – KLB456 nukreipiamas į B-01, EV vieta A-05 lieka laisva."""
    zones = [Zone(zone_id="A", priority=1), Zone(zone_id="B", priority=2)]
    spots = [
        Spot(spot_id="A-05", zone_id="A", spot_type=SpotType.EV, distance_to_entrance=15),
        Spot(spot_id="B-01", zone_id="B", spot_type=SpotType.STANDARD, distance_to_entrance=5),
    ]
    repo = InMemoryRepository(TENANT_A, zones, spots)
    service = ParkingAllocationService(repo)

    result = service.process_event(entry("KLB456", preferred_zone="A"))

    assert result.status == AllocationStatus.ASSIGNED
    assert result.spot == "B-01"
    assert result.alternative_zone is True
    assert repo.count_free_spots("A") == 1  # A-05 lieka laisva


def test_exit_without_entry_rejected_and_counts_unchanged():
    """3 scenarijus: MNC789 nėra aikštelėje → NO_ACTIVE_ENTRY, laisvų vietų skaičius nekinta."""
    zones = [Zone(zone_id="A", priority=1)]
    spots = [
        Spot(spot_id="A-01", zone_id="A", spot_type=SpotType.STANDARD, distance_to_entrance=10),
    ]
    repo = InMemoryRepository(TENANT_A, zones, spots)
    service = ParkingAllocationService(repo)

    result = service.process_event(exit_event("MNC789"))

    assert result.status == AllocationStatus.REJECTED
    assert result.error_code == ErrorCode.NO_ACTIVE_ENTRY
    assert repo.count_free_spots("A") == 1


def test_full_lot_entry_rejected_and_counts_unchanged():
    """4 scenarijus: pilna aikštelė – visos vietos užimtos, grąžinama LOT_FULL, skaičius lieka 0."""
    zones = [Zone(zone_id="A", priority=1)]
    spots = [
        Spot(
            spot_id="A-01",
            zone_id="A",
            spot_type=SpotType.STANDARD,
            distance_to_entrance=10,
            is_occupied=True,
        ),
    ]
    active = [ActiveParking(plate="XXX000", spot_id="A-01", zone_id="A")]
    repo = InMemoryRepository(TENANT_A, zones, spots, active_parkings=active)
    service = ParkingAllocationService(repo)

    result = service.process_event(entry("NEW001"))

    assert result.status == AllocationStatus.REJECTED
    assert result.error_code == ErrorCode.LOT_FULL
    assert repo.count_free_spots("A") == 0


def test_duplicate_entry_rejected_car_stays_at_original_spot():
    """5 scenarijus: dublikatas – LTA123 jau yra A-01, DUPLICATE_ENTRY, vieta nepakinta."""
    zones = [Zone(zone_id="A", priority=1)]
    spots = [
        Spot(
            spot_id="A-01",
            zone_id="A",
            spot_type=SpotType.STANDARD,
            distance_to_entrance=10,
            is_occupied=True,
        ),
        Spot(spot_id="A-02", zone_id="A", spot_type=SpotType.STANDARD, distance_to_entrance=25),
    ]
    active = [ActiveParking(plate="LTA123", spot_id="A-01", zone_id="A")]
    repo = InMemoryRepository(TENANT_A, zones, spots, active_parkings=active)
    service = ParkingAllocationService(repo)

    result = service.process_event(entry("LTA123"))

    assert result.status == AllocationStatus.REJECTED
    assert result.error_code == ErrorCode.DUPLICATE_ENTRY
    parking = repo.get_active_parking("LTA123")
    assert parking is not None
    assert parking.spot_id == "A-01"


def test_tenant_b_cannot_exit_car_parked_under_tenant_a():
    """6 scenarijus: izoliacija – kliento B EXIT LTA123 atmestas, kliento A duomenys nepakinta."""
    zones_a = [Zone(zone_id="A", priority=1)]
    spots_a = [
        Spot(
            spot_id="A-01",
            zone_id="A",
            spot_type=SpotType.STANDARD,
            distance_to_entrance=10,
            is_occupied=True,
        ),
    ]
    active_a = [ActiveParking(plate="LTA123", spot_id="A-01", zone_id="A")]
    repo_a = InMemoryRepository(TENANT_A, zones_a, spots_a, active_parkings=active_a)

    zones_b = [Zone(zone_id="A", priority=1)]
    spots_b = [
        Spot(spot_id="A-01", zone_id="A", spot_type=SpotType.STANDARD, distance_to_entrance=10),
    ]
    repo_b = InMemoryRepository(TENANT_B, zones_b, spots_b)
    service_b = ParkingAllocationService(repo_b)

    result = service_b.process_event(exit_event("LTA123", tenant_id=TENANT_B))

    assert result.status == AllocationStatus.REJECTED
    assert result.error_code == ErrorCode.NO_ACTIVE_ENTRY
    assert repo_a.get_active_parking("LTA123") is not None
    assert repo_a.count_free_spots("A") == 0


def test_ev_car_prefers_ev_spot_over_nearer_standard_spot():
    """EV pirmenybė – EV automobilis pasirenka A-02 (EV, 10 m) vietoj A-01 (STANDARD, 5 m)."""
    zones = [Zone(zone_id="A", priority=1)]
    spots = [
        Spot(spot_id="A-01", zone_id="A", spot_type=SpotType.STANDARD, distance_to_entrance=5),
        Spot(spot_id="A-02", zone_id="A", spot_type=SpotType.EV, distance_to_entrance=10),
    ]
    repo = InMemoryRepository(TENANT_A, zones, spots)
    service = ParkingAllocationService(repo)

    result = service.process_event(entry("EV001", vehicle_type=VehicleType.EV))

    assert result.status == AllocationStatus.ASSIGNED
    assert result.spot == "A-02"
    assert result.spot_type == SpotType.EV


def test_ev_car_falls_back_to_standard_when_no_ev_spots():
    """EV rezervas – EV automobilis gauna A-01 (STANDARD, 10 m), kai nėra EV vietų."""
    zones = [Zone(zone_id="A", priority=1)]
    spots = [
        Spot(spot_id="A-01", zone_id="A", spot_type=SpotType.STANDARD, distance_to_entrance=10),
        Spot(spot_id="A-02", zone_id="A", spot_type=SpotType.STANDARD, distance_to_entrance=20),
    ]
    repo = InMemoryRepository(TENANT_A, zones, spots)
    service = ParkingAllocationService(repo)

    result = service.process_event(entry("EV002", vehicle_type=VehicleType.EV))

    assert result.status == AllocationStatus.ASSIGNED
    assert result.spot == "A-01"
    assert result.spot_type == SpotType.STANDARD


def test_equal_distance_assigns_spot_with_lower_number():
    """Lygybės sprendimas – A-02 ir A-07 abi 15 m; pasirenkama A-02 (numeriškai 2 < 7)."""
    zones = [Zone(zone_id="A", priority=1)]
    spots = [
        Spot(spot_id="A-07", zone_id="A", spot_type=SpotType.STANDARD, distance_to_entrance=15),
        Spot(spot_id="A-02", zone_id="A", spot_type=SpotType.STANDARD, distance_to_entrance=15),
    ]
    repo = InMemoryRepository(TENANT_A, zones, spots)
    service = ParkingAllocationService(repo)

    result = service.process_event(entry("LTA123"))

    assert result.status == AllocationStatus.ASSIGNED
    assert result.spot == "A-02"


def test_equal_distance_numeric_order_not_lexicographic():
    """Skaitinis rikiavimas – A-9 ir A-10 abi 15 m; laimi A-9 (9 < 10, ne leksikografinis)."""
    zones = [Zone(zone_id="A", priority=1)]
    spots = [
        Spot(spot_id="A-10", zone_id="A", spot_type=SpotType.STANDARD, distance_to_entrance=15),
        Spot(spot_id="A-9", zone_id="A", spot_type=SpotType.STANDARD, distance_to_entrance=15),
    ]
    repo = InMemoryRepository(TENANT_A, zones, spots)
    service = ParkingAllocationService(repo)

    result = service.process_event(entry("LTA123"))

    assert result.status == AllocationStatus.ASSIGNED
    assert result.spot == "A-9"


def test_no_zone_picks_globally_nearest_across_all_zones():
    """Be pageidaujamos zonos: pasirenkama B-01 (5 m) vietoj A-01 (10 m); alternative_zone=False."""
    zones = [Zone(zone_id="A", priority=1), Zone(zone_id="B", priority=2)]
    spots = [
        Spot(spot_id="A-01", zone_id="A", spot_type=SpotType.STANDARD, distance_to_entrance=10),
        Spot(spot_id="A-02", zone_id="A", spot_type=SpotType.STANDARD, distance_to_entrance=20),
        Spot(spot_id="B-01", zone_id="B", spot_type=SpotType.STANDARD, distance_to_entrance=5),
    ]
    repo = InMemoryRepository(TENANT_A, zones, spots)
    service = ParkingAllocationService(repo)

    result = service.process_event(entry("LTA123", preferred_zone=None))

    assert result.status == AllocationStatus.ASSIGNED
    assert result.spot == "B-01"
    assert result.alternative_zone is False


def test_with_preferred_zone_existing_behavior_unchanged():
    """Su preferred_zone='A': priskiriama A-01 (10 m); B-01 (5 m) ignoruojama."""
    zones = [Zone(zone_id="A", priority=1), Zone(zone_id="B", priority=2)]
    spots = [
        Spot(spot_id="A-01", zone_id="A", spot_type=SpotType.STANDARD, distance_to_entrance=10),
        Spot(spot_id="A-02", zone_id="A", spot_type=SpotType.STANDARD, distance_to_entrance=20),
        Spot(spot_id="B-01", zone_id="B", spot_type=SpotType.STANDARD, distance_to_entrance=5),
    ]
    repo = InMemoryRepository(TENANT_A, zones, spots)
    service = ParkingAllocationService(repo)

    result = service.process_event(entry("LTA123", preferred_zone="A"))

    assert result.status == AllocationStatus.ASSIGNED
    assert result.spot == "A-01"
    assert result.alternative_zone is False


def test_successful_exit_releases_spot_and_increments_free_count():
    """Sėkmingas išvažiavimas – LTA123 išvažiuoja, vieta atlaisvinama, RELEASED, laisvų +1."""
    zones = [Zone(zone_id="A", priority=1)]
    spots = [
        Spot(
            spot_id="A-01",
            zone_id="A",
            spot_type=SpotType.STANDARD,
            distance_to_entrance=10,
            is_occupied=True,
        ),
    ]
    active = [ActiveParking(plate="LTA123", spot_id="A-01", zone_id="A")]
    repo = InMemoryRepository(TENANT_A, zones, spots, active_parkings=active)
    service = ParkingAllocationService(repo)

    result = service.process_event(exit_event("LTA123"))

    assert result.status == AllocationStatus.RELEASED
    assert result.spot == "A-01"
    assert result.zone == "A"
    assert result.free_in_zone == 1
    assert repo.get_active_parking("LTA123") is None
    assert repo.count_free_spots("A") == 1


def test_unknown_zone_entry_rejected_and_counts_unchanged():
    """Neegzistuojanti zona – UNKNOWN_ZONE, laisvų vietų skaičius nekinta."""
    zones = [Zone(zone_id="A", priority=1)]
    spots = [
        Spot(spot_id="A-01", zone_id="A", spot_type=SpotType.STANDARD, distance_to_entrance=10),
    ]
    repo = InMemoryRepository(TENANT_A, zones, spots)
    service = ParkingAllocationService(repo)

    result = service.process_event(entry("LTA123", preferred_zone="NERA"))

    assert result.status == AllocationStatus.REJECTED
    assert result.error_code == ErrorCode.UNKNOWN_ZONE
    assert repo.count_free_spots("A") == 1
    assert repo.get_active_parking("LTA123") is None


def test_spot_number_extracts_numeric_suffix():
    """spot_number ištraukia sveikąjį skaičių iš galiojančio vietos ID."""
    assert spot_number("A-1") == 1
    assert spot_number("A-01") == 1
    assert spot_number("B-12") == 12
    assert spot_number("ZONE-99") == 99


def test_spot_number_raises_on_invalid_id():
    """spot_number meta ValueError netinkamam vietos ID formatui."""
    with pytest.raises(ValueError):
        spot_number("NEGALIMAS")


class _NeverClaimsRepository(InMemoryRepository):
    """Stub: claim_spot visada grąžina False – imituoja nuolatinę blokavimo nesėkmę.

    Skaičiuoja iškvietimų kiekį ir kelia AssertionError viršijus 10 – tai aptinka
    begalinį ciklą be priklausomybės nuo signal.alarm (veikia ir Windows).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.claim_spot_call_count = 0

    def claim_spot(self, spot_id: str) -> bool:
        self.claim_spot_call_count += 1
        if self.claim_spot_call_count > 10:
            raise AssertionError(
                f"claim_spot iškviestas {self.claim_spot_call_count} kartų – ciklas nesibaigia"
            )
        return False


def test_claim_spot_always_false_returns_lot_full_not_hang():
    """Jei claim_spot visada grąžina False, servisas grąžina LOT_FULL, ne kaba amžinai.

    Tikrinama, kad claim_spot iškviestas lygiai tiek kartų, kiek yra tinkamų vietų (1).
    """
    zones = [Zone(zone_id="A", priority=1)]
    spots = [
        Spot(spot_id="A-01", zone_id="A", spot_type=SpotType.STANDARD, distance_to_entrance=10),
    ]
    repo = _NeverClaimsRepository(TENANT_A, zones, spots)
    service = ParkingAllocationService(repo)

    result = service.process_event(entry("T001"))

    assert result.status == AllocationStatus.REJECTED
    assert result.error_code == ErrorCode.LOT_FULL
    assert repo.claim_spot_call_count == 1
