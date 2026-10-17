"""API lygio izoliacijos testai su FastAPI TestClient."""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.api.main import app
from db.orm_models import ActiveParkingORM, Base, SpotORM, TenantORM, ZoneORM

pytestmark = pytest.mark.integration

TENANT_A = "biuru-centras-a"
TENANT_B = "prekybos-centras-b"


@pytest.fixture(scope="module")
def api_engine():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.fail(
            "TEST_DATABASE_URL is not set. Copy .env.example to .env and run: docker compose up -d"
        )
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def client(api_engine):
    with Session(api_engine) as s:
        s.execute(text("DELETE FROM active_parkings"))
        s.execute(text("DELETE FROM spots"))
        s.execute(text("DELETE FROM zones"))
        s.execute(text("DELETE FROM tenants"))
        s.add_all(
            [
                TenantORM(tenant_id=TENANT_A, name="Biurų centras A"),
                TenantORM(tenant_id=TENANT_B, name="Prekybos centras B"),
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
        s.commit()

    def override_get_db():
        with Session(api_engine) as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_occupancy_tenant_b_does_not_see_tenant_a_zones(client):
    """GET /occupancy kliento B kontekste grąžina tik kliento B zoną ir jo laisvų vietų skaičių."""
    resp = client.get("/occupancy", headers={"X-Tenant-ID": TENANT_B})
    assert resp.status_code == 200
    data = resp.json()
    assert data["tenant_id"] == TENANT_B
    assert len(data["zones"]) == 1
    assert data["zones"][0]["zone_id"] == "A"
    assert data["zones"][0]["free_spots"] == 1  # kliento B A-01 laisva


def test_exit_tenant_a_car_rejected_in_tenant_b_context(client):
    """POST /events EXIT automobiliui LTA123 (kliento A) kliento B kontekste → REJECTED."""
    resp = client.post(
        "/events",
        json={
            "event_type": "EXIT",
            "plate": "LTA123",
            "vehicle_type": "STANDARD",
            "has_disability_permit": False,
            "preferred_zone": "A",
        },
        headers={"X-Tenant-ID": TENANT_B},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "REJECTED"
    assert data["error_code"] == "NO_ACTIVE_ENTRY"


def test_unknown_tenant_returns_404(client):
    """Nežinomas X-Tenant-ID grąžina 404."""
    resp = client.get("/occupancy", headers={"X-Tenant-ID": "nera-tokio"})
    assert resp.status_code == 404
