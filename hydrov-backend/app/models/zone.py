from sqlalchemy import Integer, String, Float, DateTime, func, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from datetime import datetime

class Zone(Base):
    __tablename__ = "zones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    zone_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    municipality: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, CheckConstraint("latitude >= -90 AND latitude <= 90", name="chk_zone_b04225"), nullable=False)
    longitude: Mapped[float] = mapped_column(Float, CheckConstraint("longitude >= -180 AND longitude <= 180", name="chk_zone_f06d62"), nullable=False)
    population: Mapped[int | None] = mapped_column(Integer, CheckConstraint("population > 0", name="chk_zone_0cf4f4"), nullable=True)
    area_km2: Mapped[float | None] = mapped_column(Float, CheckConstraint("area_km2 > 0", name="chk_zone_2095cc"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
