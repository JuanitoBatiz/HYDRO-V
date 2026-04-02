from sqlalchemy import Integer, String, DateTime, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from datetime import datetime

class Valve(Base):
    __tablename__ = "valves"
    __table_args__ = (
        UniqueConstraint("device_id", "valve_type_id", name="idx_valves_device_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False)
    valve_type_id: Mapped[int] = mapped_column(ForeignKey("valve_types.id"), nullable=False)
    current_state: Mapped[str] = mapped_column(String(10), CheckConstraint("current_state IN ('open', 'closed')", name="chk_valve_177a0a"), default="closed", nullable=False)
    last_commanded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
