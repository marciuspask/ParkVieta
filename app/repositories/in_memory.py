from app.domain.models import ActiveParking, Spot, Zone
from app.repositories.base import ParkingRepository


class InMemoryRepository(ParkingRepository):
    def __init__(
        self,
        tenant_id: str,
        zones: list[Zone],
        spots: list[Spot],
        active_parkings: list[ActiveParking] | None = None,
    ):
        super().__init__(tenant_id)
        self._zones: dict[str, Zone] = {z.zone_id: z for z in zones}
        self._spots: dict[str, Spot] = {s.spot_id: s for s in spots}
        self._active_parkings: dict[str, ActiveParking] = {
            p.plate: p for p in (active_parkings or [])
        }

    def get_zone(self, zone_id: str) -> Zone | None:
        return self._zones.get(zone_id)

    def get_zones_by_priority(self) -> list[Zone]:
        return sorted(self._zones.values(), key=lambda z: z.priority)

    def get_all_spots(self, zone_id: str) -> list[Spot]:
        return sorted(
            [s for s in self._spots.values() if s.zone_id == zone_id],
            key=lambda s: (s.distance_to_entrance, s.spot_id),
        )

    def get_free_spots(self, zone_id: str) -> list[Spot]:
        return [
            s for s in self._spots.values()
            if s.zone_id == zone_id and not s.is_occupied
        ]

    def count_free_spots(self, zone_id: str) -> int:
        return len(self.get_free_spots(zone_id))

    def get_active_parking(self, plate: str) -> ActiveParking | None:
        return self._active_parkings.get(plate)

    def claim_spot(self, spot_id: str) -> bool:
        spot = self._spots[spot_id]
        if spot.is_occupied:
            return False
        spot.is_occupied = True
        return True

    def mark_spot_free(self, spot_id: str) -> None:
        self._spots[spot_id].is_occupied = False

    def save_active_parking(self, parking: ActiveParking) -> None:
        self._active_parkings[parking.plate] = parking

    def remove_active_parking(self, plate: str) -> None:
        self._active_parkings.pop(plate, None)
