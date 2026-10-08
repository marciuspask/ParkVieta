from abc import ABC, abstractmethod

from app.domain.models import Spot, SpotType, Vehicle, VehicleType


class SpotEligibilityRule(ABC):
    @abstractmethod
    def is_eligible(self, vehicle: Vehicle, spot: Spot) -> bool: ...


class StandardRule(SpotEligibilityRule):
    def is_eligible(self, vehicle: Vehicle, spot: Spot) -> bool:
        return spot.spot_type == SpotType.STANDARD


class EVRule(SpotEligibilityRule):
    def is_eligible(self, vehicle: Vehicle, spot: Spot) -> bool:
        return spot.spot_type == SpotType.EV and vehicle.vehicle_type == VehicleType.EV


class DisabledRule(SpotEligibilityRule):
    def is_eligible(self, vehicle: Vehicle, spot: Spot) -> bool:
        return spot.spot_type == SpotType.DISABLED and vehicle.has_disability_permit


ELIGIBILITY_RULES: dict[SpotType, SpotEligibilityRule] = {
    SpotType.STANDARD: StandardRule(),
    SpotType.EV: EVRule(),
    SpotType.DISABLED: DisabledRule(),
}
