from app.domain.models import ActiveParking, Spot, Zone
from app.repositories.base import ParkingRepository


class PostgreSQLRepository(ParkingRepository):
    def get_zone(self, zone_id: str) -> Zone | None:
        raise NotImplementedError

    def get_zones_by_priority(self) -> list[Zone]:
        raise NotImplementedError

    def get_free_spots(self, zone_id: str) -> list[Spot]:
        raise NotImplementedError

    def count_free_spots(self, zone_id: str) -> int:
        raise NotImplementedError

    def get_active_parking(self, plate: str) -> ActiveParking | None:
        raise NotImplementedError

    def mark_spot_occupied(self, spot_id: str) -> None:
        raise NotImplementedError

    def mark_spot_free(self, spot_id: str) -> None:
        raise NotImplementedError

    def save_active_parking(self, parking: ActiveParking) -> None:
        raise NotImplementedError

    def remove_active_parking(self, plate: str) -> None:
        raise NotImplementedError
