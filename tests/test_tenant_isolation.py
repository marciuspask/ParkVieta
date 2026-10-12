"""Integration tests: tenant isolation and concurrency via real PostgreSQL.

Requires TEST_DATABASE_URL environment variable.
Example: TEST_DATABASE_URL=postgresql://postgres:password@localhost:5432/parkvieta_test
"""
import os
import threading
from datetime import datetime

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.domain.models import (
    AllocationStatus,
    ErrorCode,
    EventType,
    ParkingEvent,
    VehicleType,
)
from app.repositories.postgres import PostgreSQLRepository
from app.services.parking_allocation import ParkingAllocationService
from db.orm_models import ActiveParkingORM, Base, SpotORM, ZoneORM

TENANT_A = "biuru-centras-a"
TENANT_B = "prekybos-centras-b"
TS = datetime(2026, 11, 10, 8, 15)

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL not set – requires PostgreSQL test database",
)


@pytest.fixture(scope="module")
def db_engine():
    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


def _clean(session: Session) -> None:
    session.execute(text("DELETE FROM active_parkings"))
    session.execute(text("DELETE FROM spots"))
    session.execute(text("DELETE FROM zones"))
    session.commit()


@pytest.fixture
def db_session(db_engine):
    """Two clients seeded: Tenant A has LTA123 parked at A-01; Tenant B has A-01 free."""
    with Session(db_engine) as session:
        _clean(session)
        session.add_all([
            ZoneORM(tenant_id=TENANT_A, zone_id="A", priority=1),
            SpotORM(tenant_id=TENANT_A, zone_id="A", spot_id="A-01",
                    spot_type="STANDARD", distance_to_entrance=10, is_occupied=True),
            ActiveParkingORM(tenant_id=TENANT_A, plate="LTA123",
                             spot_id="A-01", zone_id="A"),
            ZoneORM(tenant_id=TENANT_B, zone_id="A", priority=1),
            SpotORM(tenant_id=TENANT_B, zone_id="A", spot_id="A-01",
                    spot_type="STANDARD", distance_to_entrance=10, is_occupied=False),
        ])
        session.commit()
        yield session


@pytest.fixture
def one_free_spot(db_engine):
    """One free STANDARD spot for Tenant A. Yields the engine so threads create own sessions."""
    with Session(db_engine) as session:
        _clean(session)
        session.add_all([
            ZoneORM(tenant_id=TENANT_A, zone_id="A", priority=1),
            SpotORM(tenant_id=TENANT_A, zone_id="A", spot_id="A-01",
                    spot_type="STANDARD", distance_to_entrance=10, is_occupied=False),
        ])
        session.commit()
    return db_engine


# --- isolation: read ---

def test_tenant_b_cannot_read_tenant_a_active_parking(db_session):
    """Client B's repository returns None for a plate parked under Client A."""
    repo_b = PostgreSQLRepository(TENANT_B, db_session)
    assert repo_b.get_active_parking("LTA123") is None


# --- isolation: exit ---

def test_tenant_b_exit_rejected_and_tenant_a_data_unchanged(db_session):
    """Client B EXIT for LTA123 → REJECTED; Client A spot stays occupied."""
    repo_b = PostgreSQLRepository(TENANT_B, db_session)
    repo_a = PostgreSQLRepository(TENANT_A, db_session)

    result = repo_b_exit(repo_b, "LTA123")

    assert result.status == AllocationStatus.REJECTED
    assert result.error_code == ErrorCode.NO_ACTIVE_ENTRY
    assert repo_a.get_active_parking("LTA123") is not None
    assert repo_a.count_free_spots("A") == 0


def repo_b_exit(repo_b, plate):
    service_b = ParkingAllocationService(repo_b)
    return service_b.process_event(ParkingEvent(
        tenant_id=TENANT_B, event_type=EventType.EXIT, plate=plate,
        vehicle_type=VehicleType.STANDARD, has_disability_permit=False,
        preferred_zone="A", timestamp=TS,
    ))


# --- isolation: entry ---

def test_tenant_b_entry_uses_own_spot_and_tenant_a_spot_unchanged(db_session):
    """Client B ENTRY claims B's A-01; Client A's A-01 (occupied) and free count unchanged."""
    repo_b = PostgreSQLRepository(TENANT_B, db_session)
    repo_a = PostgreSQLRepository(TENANT_A, db_session)
    service_b = ParkingAllocationService(repo_b)

    result = service_b.process_event(ParkingEvent(
        tenant_id=TENANT_B, event_type=EventType.ENTRY, plate="NEW001",
        vehicle_type=VehicleType.STANDARD, has_disability_permit=False,
        preferred_zone="A", timestamp=TS,
    ))

    assert result.status == AllocationStatus.ASSIGNED
    assert result.spot == "A-01"
    db_session.commit()

    assert repo_a.get_active_parking("LTA123") is not None
    assert repo_a.count_free_spots("A") == 0


# --- concurrency ---

def test_concurrent_entries_one_spot_exactly_one_assigned(one_free_spot):
    """Two concurrent entries to a 1-spot zone: exactly one ASSIGNED, one LOT_FULL."""
    engine = one_free_spot
    results: dict[str, object] = {}
    barrier = threading.Barrier(2)

    def entry_thread(plate: str) -> None:
        with Session(engine) as session:
            repo = PostgreSQLRepository(TENANT_A, session)
            service = ParkingAllocationService(repo)
            event = ParkingEvent(
                tenant_id=TENANT_A, event_type=EventType.ENTRY, plate=plate,
                vehicle_type=VehicleType.STANDARD, has_disability_permit=False,
                preferred_zone="A", timestamp=TS,
            )
            barrier.wait()
            result = service.process_event(event)
            session.commit()
            results[plate] = result

    threads = [threading.Thread(target=entry_thread, args=(f"CAR00{i}",)) for i in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assigned = sum(1 for r in results.values() if r.status == AllocationStatus.ASSIGNED)
    lot_full = sum(
        1 for r in results.values()
        if r.status == AllocationStatus.REJECTED and r.error_code == ErrorCode.LOT_FULL
    )

    assert assigned == 1, f"Expected 1 ASSIGNED, got {assigned}: {results}"
    assert lot_full == 1, f"Expected 1 LOT_FULL, got {lot_full}: {results}"
