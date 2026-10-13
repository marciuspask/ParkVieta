from pydantic import BaseModel

from app.domain.models import EventType, VehicleType


class ParkingEventIn(BaseModel):
    event_type: EventType
    plate: str
    vehicle_type: VehicleType = VehicleType.STANDARD
    has_disability_permit: bool = False
    preferred_zone: str | None = None


class SpotInfo(BaseModel):
    spot_id: str
    spot_type: str
    distance_to_entrance: int
    is_occupied: bool


class ZoneOccupancy(BaseModel):
    zone_id: str
    priority: int
    free_spots: int
    spots: list[SpotInfo]


class OccupancyResponse(BaseModel):
    tenant_id: str
    zones: list[ZoneOccupancy]
