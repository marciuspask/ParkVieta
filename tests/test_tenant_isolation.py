"""Integraciniai testai: nuomininko izoliacija ir lygiagretumas su realia PostgreSQL DB.

Reikalingas TEST_DATABASE_URL aplinkos kintamasis.
Pavyzdys: TEST_DATABASE_URL=postgresql://postgres:password@localhost:5432/parkvieta_test
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

pytestmark = pytest.mark.integration

TENANT_A = "biuru-centras-a"
TENANT_B = "prekybos-centras-b"
SAMPLE_TIMESTAMP = datetime(2026, 11, 10, 8, 15)


@pytest.fixture(scope="module")
def db_engine():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.fail(
            "TEST_DATABASE_URL is not set. Copy .env.example to .env and run: docker compose up -d"
        )
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


def _clean(session: Session) -> None:
    session.execute(text("DELETE FROM active_parkings"))
    session.execute(text("DELETE FROM spots"))
    session.execute(text("DELETE FROM zones"))
    session.execute(text("DELETE FROM tenants"))
    session.commit()


@pytest.fixture
def db_session(db_engine):
    """Du klientai: kliento A LTA123 yra A-01; kliento B A-01 laisva."""
    with Session(db_engine) as session:
        _clean(session)
        session.add_all(
            [
                ZoneORM(tenant_id=TENANT_A, zone_id="A", priority=1),
                SpotORM(
                    tenant_id=TENANT_A,
                    zone_id="A",
                    spot_id="A-01",
                    spot_type="STANDARD",
                    distance_to_entrance=10,
                    is_occupied=True,
                ),
                ActiveParkingORM(tenant_id=TENANT_A, plate="LTA123", spot_id="A-01", zone_id="A"),
                ZoneORM(tenant_id=TENANT_B, zone_id="A", priority=1),
                SpotORM(
                    tenant_id=TENANT_B,
                    zone_id="A",
                    spot_id="A-01",
                    spot_type="STANDARD",
                    distance_to_entrance=10,
                    is_occupied=False,
                ),
            ]
        )
        session.commit()
        yield session


@pytest.fixture
def one_free_spot(db_engine):
    """Viena laisva STANDARD vieta klientui A. Grąžina engine, kad gijos kurtų atskiras sesijas."""
    with Session(db_engine) as session:
        _clean(session)
        session.add_all(
            [
                ZoneORM(tenant_id=TENANT_A, zone_id="A", priority=1),
                SpotORM(
                    tenant_id=TENANT_A,
                    zone_id="A",
                    spot_id="A-01",
                    spot_type="STANDARD",
                    distance_to_entrance=10,
                    is_occupied=False,
                ),
            ]
        )
        session.commit()
    return db_engine


# --- isolation: read ---


def test_tenant_b_cannot_read_tenant_a_active_parking(db_session):
    """Kliento B repozitorija grąžina None valstybiniam numeriui, kuris priskirtas klientui A."""
    repo_b = PostgreSQLRepository(TENANT_B, db_session)
    assert repo_b.get_active_parking("LTA123") is None


# --- isolation: exit ---


def test_tenant_b_exit_rejected_and_tenant_a_data_unchanged(db_session):
    """Kliento B EXIT LTA123 → REJECTED; kliento A vieta lieka užimta."""
    repo_b = PostgreSQLRepository(TENANT_B, db_session)
    repo_a = PostgreSQLRepository(TENANT_A, db_session)

    result = exit_vehicle(repo_b, TENANT_B, "LTA123")

    assert result.status == AllocationStatus.REJECTED
    assert result.error_code == ErrorCode.NO_ACTIVE_ENTRY
    assert repo_a.get_active_parking("LTA123") is not None
    assert repo_a.count_free_spots("A") == 0


def exit_vehicle(repo, tenant_id, plate):
    service = ParkingAllocationService(repo)
    return service.process_event(
        ParkingEvent(
            tenant_id=tenant_id,
            event_type=EventType.EXIT,
            plate=plate,
            vehicle_type=VehicleType.STANDARD,
            has_disability_permit=False,
            preferred_zone="A",
            timestamp=SAMPLE_TIMESTAMP,
        )
    )


# --- isolation: entry ---


def test_tenant_b_entry_uses_own_spot_and_tenant_a_spot_unchanged(db_session):
    """Kliento B ENTRY užima B A-01; kliento A A-01 (užimta) ir laisvų skaičius nepakinta."""
    repo_b = PostgreSQLRepository(TENANT_B, db_session)
    repo_a = PostgreSQLRepository(TENANT_A, db_session)
    service_b = ParkingAllocationService(repo_b)

    result = service_b.process_event(
        ParkingEvent(
            tenant_id=TENANT_B,
            event_type=EventType.ENTRY,
            plate="NEW001",
            vehicle_type=VehicleType.STANDARD,
            has_disability_permit=False,
            preferred_zone="A",
            timestamp=SAMPLE_TIMESTAMP,
        )
    )

    assert result.status == AllocationStatus.ASSIGNED
    assert result.spot == "A-01"
    db_session.commit()

    assert repo_a.get_active_parking("LTA123") is not None
    assert repo_a.count_free_spots("A") == 0


# --- concurrency ---


def test_concurrent_entries_one_spot_exactly_one_assigned(one_free_spot):
    """Du lygiagretūs įvažiavimai į 1 vietos zoną: lygiai vienas ASSIGNED, vienas LOT_FULL."""
    engine = one_free_spot
    results: dict[str, object] = {}
    barrier = threading.Barrier(2)

    def entry_thread(plate: str) -> None:
        with Session(engine) as session:
            repo = PostgreSQLRepository(TENANT_A, session)
            service = ParkingAllocationService(repo)
            event = ParkingEvent(
                tenant_id=TENANT_A,
                event_type=EventType.ENTRY,
                plate=plate,
                vehicle_type=VehicleType.STANDARD,
                has_disability_permit=False,
                preferred_zone="A",
                timestamp=SAMPLE_TIMESTAMP,
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
        1
        for r in results.values()
        if r.status == AllocationStatus.REJECTED and r.error_code == ErrorCode.LOT_FULL
    )

    assert assigned == 1, f"Expected 1 ASSIGNED, got {assigned}: {results}"
    assert lot_full == 1, f"Expected 1 LOT_FULL, got {lot_full}: {results}"
