from sqlalchemy.orm import Session

from db.database import get_engine
from db.orm_models import ActiveParkingORM, Base, SpotORM, ZoneORM


def seed(session: Session) -> None:
    session.query(ActiveParkingORM).delete()
    session.query(SpotORM).delete()
    session.query(ZoneORM).delete()

    session.add_all([
        # --- Biurų centras A: zonos A (6 vietų) ir B (4 vietos), iš viso 10 ---
        ZoneORM(tenant_id="biuru-centras-a", zone_id="A", priority=1),
        ZoneORM(tenant_id="biuru-centras-a", zone_id="B", priority=2),

        SpotORM(tenant_id="biuru-centras-a", zone_id="A", spot_id="A-01",
                spot_type="STANDARD", distance_to_entrance=10),
        SpotORM(tenant_id="biuru-centras-a", zone_id="A", spot_id="A-02",
                spot_type="STANDARD", distance_to_entrance=20),
        SpotORM(tenant_id="biuru-centras-a", zone_id="A", spot_id="A-03",
                spot_type="STANDARD", distance_to_entrance=30),
        SpotORM(tenant_id="biuru-centras-a", zone_id="A", spot_id="A-04",
                spot_type="EV", distance_to_entrance=15),
        SpotORM(tenant_id="biuru-centras-a", zone_id="A", spot_id="A-05",
                spot_type="EV", distance_to_entrance=25),
        SpotORM(tenant_id="biuru-centras-a", zone_id="A", spot_id="A-06",
                spot_type="DISABLED", distance_to_entrance=8),

        SpotORM(tenant_id="biuru-centras-a", zone_id="B", spot_id="B-01",
                spot_type="STANDARD", distance_to_entrance=5),
        SpotORM(tenant_id="biuru-centras-a", zone_id="B", spot_id="B-02",
                spot_type="STANDARD", distance_to_entrance=15),
        SpotORM(tenant_id="biuru-centras-a", zone_id="B", spot_id="B-03",
                spot_type="STANDARD", distance_to_entrance=25),
        SpotORM(tenant_id="biuru-centras-a", zone_id="B", spot_id="B-04",
                spot_type="STANDARD", distance_to_entrance=35),

        # --- Prekybos centras B: zona A (5 vietos) ---
        ZoneORM(tenant_id="prekybos-centras-b", zone_id="A", priority=1),

        SpotORM(tenant_id="prekybos-centras-b", zone_id="A", spot_id="A-01",
                spot_type="STANDARD", distance_to_entrance=12),
        SpotORM(tenant_id="prekybos-centras-b", zone_id="A", spot_id="A-02",
                spot_type="STANDARD", distance_to_entrance=20),
        SpotORM(tenant_id="prekybos-centras-b", zone_id="A", spot_id="A-03",
                spot_type="STANDARD", distance_to_entrance=28),
        SpotORM(tenant_id="prekybos-centras-b", zone_id="A", spot_id="A-04",
                spot_type="STANDARD", distance_to_entrance=36),
        SpotORM(tenant_id="prekybos-centras-b", zone_id="A", spot_id="A-05",
                spot_type="STANDARD", distance_to_entrance=44),
    ])
    session.commit()


if __name__ == "__main__":
    engine = get_engine()
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        seed(s)
    print("Seed duomenys įkelti.")
