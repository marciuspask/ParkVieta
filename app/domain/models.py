from dataclasses import dataclass
from datetime import datetime
from enum import Enum


def spot_number(spot_id: str) -> int:
    """Grąžina numerinę vietos ID dalį (pvz. 'A-01' → 1, 'B-12' → 12)."""
    try:
        return int(spot_id.split("-")[-1])
    except (ValueError, IndexError):
        raise ValueError(f"Nepavyksta išgauti numerio iš vietos ID: {spot_id!r}")


class VehicleType(str, Enum):
    STANDARD = "STANDARD"
    EV = "EV"


class SpotType(str, Enum):
    STANDARD = "STANDARD"
    EV = "EV"
    DISABLED = "DISABLED"


class EventType(str, Enum):
    ENTRY = "ENTRY"
    EXIT = "EXIT"


class AllocationStatus(str, Enum):
    ASSIGNED = "ASSIGNED"
    RELEASED = "RELEASED"
    REJECTED = "REJECTED"


class ErrorCode(str, Enum):
    DUPLICATE_ENTRY = "DUPLICATE_ENTRY"
    NO_ACTIVE_ENTRY = "NO_ACTIVE_ENTRY"
    UNKNOWN_ZONE = "UNKNOWN_ZONE"
    LOT_FULL = "LOT_FULL"


@dataclass
class Vehicle:
    plate: str
    vehicle_type: VehicleType
    has_disability_permit: bool


@dataclass
class Zone:
    zone_id: str
    priority: int


@dataclass
class Spot:
    spot_id: str
    zone_id: str
    spot_type: SpotType
    distance_to_entrance: int
    is_occupied: bool = False


@dataclass
class ActiveParking:
    plate: str
    spot_id: str
    zone_id: str


@dataclass
class ParkingEvent:
    tenant_id: str
    event_type: EventType
    plate: str
    vehicle_type: VehicleType
    has_disability_permit: bool
    preferred_zone: str | None
    timestamp: datetime


@dataclass
class AllocationResult:
    status: AllocationStatus
    zone: str | None = None
    spot: str | None = None
    spot_type: SpotType | None = None
    free_in_zone: int | None = None
    alternative_zone: bool = False
    error_code: ErrorCode | None = None
    message: str | None = None
