from dataclasses import asdict
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from app.api.dependencies import get_repository, get_tenant_id
from app.api.schemas import OccupancyResponse, ParkingEventIn, SpotInfo, ZoneOccupancy
from app.domain.models import ParkingEvent
from app.repositories.base import ParkingRepository
from app.services.parking_allocation import ParkingAllocationService

router = APIRouter()


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def serve_ui():
    with open("static/index.html", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@router.post("/events")
def handle_event(
    payload: ParkingEventIn,
    tenant_id: str = Depends(get_tenant_id),
    repo: ParkingRepository = Depends(get_repository),
):
    service = ParkingAllocationService(repo)
    domain_event = ParkingEvent(
        tenant_id=tenant_id,
        event_type=payload.event_type,
        plate=payload.plate,
        vehicle_type=payload.vehicle_type,
        has_disability_permit=payload.has_disability_permit,
        preferred_zone=payload.preferred_zone,
        timestamp=datetime.now(),
    )
    result = service.process_event(domain_event)
    return asdict(result)


@router.get("/occupancy", response_model=OccupancyResponse)
def get_occupancy(
    tenant_id: str = Depends(get_tenant_id),
    repo: ParkingRepository = Depends(get_repository),
):
    zones = repo.get_zones_by_priority()
    return OccupancyResponse(
        tenant_id=tenant_id,
        zones=[
            ZoneOccupancy(
                zone_id=z.zone_id,
                priority=z.priority,
                free_spots=repo.count_free_spots(z.zone_id),
                spots=[
                    SpotInfo(
                        spot_id=s.spot_id,
                        spot_type=s.spot_type.value,
                        distance_to_entrance=s.distance_to_entrance,
                        is_occupied=s.is_occupied,
                    )
                    for s in repo.get_all_spots(z.zone_id)
                ],
            )
            for z in zones
        ],
    )
