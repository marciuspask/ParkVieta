from app.domain.errors import ParkingError
from app.domain.models import (
    ActiveParking,
    AllocationResult,
    AllocationStatus,
    ErrorCode,
    EventType,
    ParkingEvent,
    Spot,
    SpotType,
    Vehicle,
)
from app.domain.rules import ELIGIBILITY_RULES
from app.repositories.base import ParkingRepository


class ParkingAllocationService:
    def __init__(self, repository: ParkingRepository):
        self._repository = repository

    def process_event(self, event: ParkingEvent) -> AllocationResult:
        try:
            if event.event_type == EventType.EXIT:
                return self._process_exit(event)
            return self._process_entry(event)
        except ParkingError as exc:
            return AllocationResult(
                status=AllocationStatus.REJECTED,
                error_code=exc.error_code,
                message=exc.message,
            )

    # --- exit ---

    def _process_exit(self, event: ParkingEvent) -> AllocationResult:
        parking = self._repository.get_active_parking(event.plate)
        if parking is None:
            raise ParkingError(
                ErrorCode.NO_ACTIVE_ENTRY,
                f"Automobilis {event.plate} neturi aktyvaus įvažiavimo",
            )
        self._repository.mark_spot_free(parking.spot_id)
        self._repository.remove_active_parking(event.plate)
        return AllocationResult(
            status=AllocationStatus.RELEASED,
            zone=parking.zone_id,
            spot=parking.spot_id,
            free_in_zone=self._repository.count_free_spots(parking.zone_id),
        )

    # --- entry ---

    def _process_entry(self, event: ParkingEvent) -> AllocationResult:
        if event.preferred_zone is not None and self._repository.get_zone(event.preferred_zone) is None:
            raise ParkingError(
                ErrorCode.UNKNOWN_ZONE,
                f"Zona {event.preferred_zone} nerasta",
            )
        if self._repository.get_active_parking(event.plate) is not None:
            raise ParkingError(
                ErrorCode.DUPLICATE_ENTRY,
                f"Automobilis {event.plate} jau yra aikštelėje",
            )

        vehicle = Vehicle(
            plate=event.plate,
            vehicle_type=event.vehicle_type,
            has_disability_permit=event.has_disability_permit,
        )
        spot, is_alternative = self._assign_spot(vehicle, event.preferred_zone)
        while not self._repository.claim_spot(spot.spot_id):
            spot, is_alternative = self._assign_spot(vehicle, event.preferred_zone)

        self._repository.save_active_parking(
            ActiveParking(plate=event.plate, spot_id=spot.spot_id, zone_id=spot.zone_id)
        )
        return AllocationResult(
            status=AllocationStatus.ASSIGNED,
            zone=spot.zone_id,
            spot=spot.spot_id,
            spot_type=spot.spot_type,
            free_in_zone=self._repository.count_free_spots(spot.zone_id),
            alternative_zone=is_alternative,
        )

    # --- spot selection (rules 3 and 4) ---

    def _assign_spot(self, vehicle: Vehicle, preferred_zone: str | None) -> tuple[Spot, bool]:
        if preferred_zone is None:
            spot = self._find_best_spot_globally(vehicle)
            if spot is not None:
                return spot, False
            raise ParkingError(ErrorCode.LOT_FULL, "Aikštelė pilna, nėra tinkamų laisvų vietų")

        spot = self._find_best_spot(vehicle, preferred_zone)
        if spot is not None:
            return spot, False

        for zone in self._repository.get_zones_by_priority():
            if zone.zone_id == preferred_zone:
                continue
            spot = self._find_best_spot(vehicle, zone.zone_id)
            if spot is not None:
                return spot, True

        raise ParkingError(ErrorCode.LOT_FULL, "Aikštelė pilna, nėra tinkamų laisvų vietų")

    def _find_best_spot_globally(self, vehicle: Vehicle) -> Spot | None:
        all_free: list[Spot] = []
        for zone in self._repository.get_zones_by_priority():
            all_free.extend(self._repository.get_free_spots(zone.zone_id))
        return self._select_best(vehicle, all_free)

    def _find_best_spot(self, vehicle: Vehicle, zone_id: str) -> Spot | None:
        return self._select_best(vehicle, self._repository.get_free_spots(zone_id))

    def _select_best(self, vehicle: Vehicle, spots: list[Spot]) -> Spot | None:
        preferred = [
            s for s in spots
            if s.spot_type != SpotType.STANDARD
            and ELIGIBILITY_RULES[s.spot_type].is_eligible(vehicle, s)
        ]
        if preferred:
            return self._nearest(preferred)
        standard = [s for s in spots if s.spot_type == SpotType.STANDARD]
        return self._nearest(standard) if standard else None

    @staticmethod
    def _nearest(spots: list[Spot]) -> Spot:
        return min(
            spots,
            key=lambda s: (s.distance_to_entrance, int(s.spot_id.split("-")[-1])),
        )
