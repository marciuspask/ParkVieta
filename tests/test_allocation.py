from datetime import datetime

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
)
from app.repositories.in_memory import InMemoryRepository
from app.services.parking_allocation import ParkingAllocationService

TENANT_A = "biuru-centras-a"
TENANT_B = "prekybos-centras-b"
TS = datetime(2026, 11, 10, 8, 15)


def entry(plate, vehicle_type=VehicleType.STANDARD, has_disability_permit=False,
          preferred_zone="A", tenant_id=TENANT_A):
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
    """Scenario 1: Normal – LTA123 gets A-01 (10 m), 2 free spots remain in zone A."""
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
    """Scenario 2: EV conflict – KLB456 redirected to B-01, EV spot A-05 stays free."""
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
    """Scenario 3: Error – MNC789 not in lot, NO_ACTIVE_ENTRY, free count unchanged."""
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
    """Scenario 4: Full lot – all spots occupied, LOT_FULL returned, count stays 0."""
    zones = [Zone(zone_id="A", priority=1)]
    spots = [
        Spot(spot_id="A-01", zone_id="A", spot_type=SpotType.STANDARD,
             distance_to_entrance=10, is_occupied=True),
    ]
    active = [ActiveParking(plate="XXX000", spot_id="A-01", zone_id="A")]
    repo = InMemoryRepository(TENANT_A, zones, spots, active_parkings=active)
    service = ParkingAllocationService(repo)

    result = service.process_event(entry("NEW001"))

    assert result.status == AllocationStatus.REJECTED
    assert result.error_code == ErrorCode.LOT_FULL
    assert repo.count_free_spots("A") == 0


def test_duplicate_entry_rejected_car_stays_at_original_spot():
    """Scenario 5: Duplicate – LTA123 already at A-01, DUPLICATE_ENTRY, spot unchanged."""
    zones = [Zone(zone_id="A", priority=1)]
    spots = [
        Spot(spot_id="A-01", zone_id="A", spot_type=SpotType.STANDARD,
             distance_to_entrance=10, is_occupied=True),
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
    """Scenario 6: Isolation – Client B's EXIT for LTA123 rejected, Client A data unchanged."""
    zones_a = [Zone(zone_id="A", priority=1)]
    spots_a = [
        Spot(spot_id="A-01", zone_id="A", spot_type=SpotType.STANDARD,
             distance_to_entrance=10, is_occupied=True),
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
    """EV preference – EV car picks A-02 (EV, 10 m) over A-01 (STANDARD, 5 m)."""
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
    """EV fallback – EV car gets A-01 (STANDARD, 10 m) when no EV spots exist."""
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
    """Tiebreak – A-02 and A-07 both at 15 m; A-02 is picked (numeric: 2 < 7)."""
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
    """Tiebreak numeric – A-9 and A-10 both at 15 m; A-9 wins (9 < 10, not '9' > '1')."""
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
    """No preferred zone: B-01 (5 m) is picked over A-01 (10 m); alternative_zone is False."""
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
    """With preferred_zone='A': A-01 (10 m) is assigned; B-01 (5 m) is ignored."""
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
    """Successful exit – LTA123 leaves, spot freed, status RELEASED, free count +1."""
    zones = [Zone(zone_id="A", priority=1)]
    spots = [
        Spot(spot_id="A-01", zone_id="A", spot_type=SpotType.STANDARD,
             distance_to_entrance=10, is_occupied=True),
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
