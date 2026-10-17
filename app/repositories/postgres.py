from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import ActiveParking, Spot, SpotType, Zone, spot_number
from app.repositories.base import ParkingRepository
from db.orm_models import ActiveParkingORM, SpotORM, ZoneORM


class PostgreSQLRepository(ParkingRepository):
    def __init__(self, tenant_id: str, session: Session):
        super().__init__(tenant_id)
        self._session = session

    def get_zone(self, zone_id: str) -> Zone | None:
        row = self._session.execute(
            self._zone_q().where(ZoneORM.zone_id == zone_id)
        ).scalar_one_or_none()
        return Zone(zone_id=row.zone_id, priority=row.priority) if row else None

    def get_zones_by_priority(self) -> list[Zone]:
        rows = self._session.execute(self._zone_q().order_by(ZoneORM.priority)).scalars().all()
        return [Zone(zone_id=r.zone_id, priority=r.priority) for r in rows]

    def get_all_spots(self, zone_id: str) -> list[Spot]:
        return self._query_spots(zone_id)

    def get_free_spots(self, zone_id: str) -> list[Spot]:
        return self._query_spots(zone_id, occupied=False)

    def count_free_spots(self, zone_id: str) -> int:
        return len(self.get_free_spots(zone_id))

    def claim_spot(self, spot_id: str) -> bool:
        row = self._session.execute(
            self._spot_q().where(SpotORM.spot_id == spot_id).with_for_update()
        ).scalar_one()
        if row.is_occupied:
            return False
        row.is_occupied = True
        return True

    def mark_spot_free(self, spot_id: str) -> None:
        row = self._session.execute(self._spot_q().where(SpotORM.spot_id == spot_id)).scalar_one()
        row.is_occupied = False

    def get_active_parking(self, plate: str) -> ActiveParking | None:
        row = self._session.execute(
            self._parking_q().where(ActiveParkingORM.plate == plate)
        ).scalar_one_or_none()
        if row is None:
            return None
        return ActiveParking(plate=row.plate, spot_id=row.spot_id, zone_id=row.zone_id)

    def save_active_parking(self, parking: ActiveParking) -> None:
        self._session.add(
            ActiveParkingORM(
                tenant_id=self._tenant_id,
                plate=parking.plate,
                spot_id=parking.spot_id,
                zone_id=parking.zone_id,
            )
        )

    def remove_active_parking(self, plate: str) -> None:
        row = self._session.execute(
            self._parking_q().where(ActiveParkingORM.plate == plate)
        ).scalar_one_or_none()
        if row is not None:
            self._session.delete(row)

    # --- shared spot filter (every spot query goes through this) ---

    def _query_spots(self, zone_id: str, occupied: bool | None = None) -> list[Spot]:
        q = self._spot_q().where(SpotORM.zone_id == zone_id)
        if occupied is not None:
            q = q.where(SpotORM.is_occupied.is_(occupied))
        spots = [self._to_spot(r) for r in self._session.execute(q).scalars().all()]
        return sorted(spots, key=lambda s: (s.distance_to_entrance, spot_number(s.spot_id)))

    # --- tenant-scoped query builders (every query goes through these) ---

    def _zone_q(self):
        return select(ZoneORM).where(ZoneORM.tenant_id == self._tenant_id)

    def _spot_q(self):
        return select(SpotORM).where(SpotORM.tenant_id == self._tenant_id)

    def _parking_q(self):
        return select(ActiveParkingORM).where(ActiveParkingORM.tenant_id == self._tenant_id)

    @staticmethod
    def _to_spot(row: SpotORM) -> Spot:
        return Spot(
            spot_id=row.spot_id,
            zone_id=row.zone_id,
            spot_type=SpotType(row.spot_type),
            distance_to_entrance=row.distance_to_entrance,
            is_occupied=row.is_occupied,
        )
