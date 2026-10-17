from abc import ABC, abstractmethod

from app.domain.models import ActiveParking, Spot, Zone


class ParkingRepository(ABC):
    def __init__(self, tenant_id: str):
        self._tenant_id = tenant_id

    @abstractmethod
    def get_zone(self, zone_id: str) -> Zone | None: ...

    @abstractmethod
    def get_zones_by_priority(self) -> list[Zone]: ...

    @abstractmethod
    def get_all_spots(self, zone_id: str) -> list[Spot]: ...

    @abstractmethod
    def get_free_spots(self, zone_id: str) -> list[Spot]: ...

    @abstractmethod
    def count_free_spots(self, zone_id: str) -> int: ...

    @abstractmethod
    def get_active_parking(self, plate: str) -> ActiveParking | None: ...

    @abstractmethod
    def claim_spot(self, spot_id: str) -> bool:
        """Užrakina eilutę ir žymi kaip užimtą. Grąžina False, jei jau užimta."""
        ...

    @abstractmethod
    def mark_spot_free(self, spot_id: str) -> None: ...

    @abstractmethod
    def save_active_parking(self, parking: ActiveParking) -> None: ...

    @abstractmethod
    def remove_active_parking(self, plate: str) -> None: ...
