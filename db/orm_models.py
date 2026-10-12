from sqlalchemy import Boolean, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ZoneORM(Base):
    __tablename__ = "zones"
    __table_args__ = (
        UniqueConstraint("tenant_id", "zone_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False)
    zone_id: Mapped[str] = mapped_column(String(50), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False)


class SpotORM(Base):
    __tablename__ = "spots"
    __table_args__ = (
        UniqueConstraint("tenant_id", "spot_id"),
        Index("ix_spots_tenant_zone_occupied", "tenant_id", "zone_id", "is_occupied"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False)
    zone_id: Mapped[str] = mapped_column(String(50), nullable=False)
    spot_id: Mapped[str] = mapped_column(String(50), nullable=False)
    spot_type: Mapped[str] = mapped_column(String(20), nullable=False)
    distance_to_entrance: Mapped[int] = mapped_column(Integer, nullable=False)
    is_occupied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class ActiveParkingORM(Base):
    __tablename__ = "active_parkings"
    __table_args__ = (
        UniqueConstraint("tenant_id", "plate"),
        UniqueConstraint("tenant_id", "spot_id"),
        Index("ix_active_parkings_tenant_plate", "tenant_id", "plate"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False)
    plate: Mapped[str] = mapped_column(String(20), nullable=False)
    spot_id: Mapped[str] = mapped_column(String(50), nullable=False)
    zone_id: Mapped[str] = mapped_column(String(50), nullable=False)
