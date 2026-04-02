from sqlalchemy import Integer, String, Float, Text, Boolean, DateTime, ForeignKey, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from datetime import datetime
from sqlalchemy.sql import func

class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False, index=True)
    sensor_id: Mapped[int | None] = mapped_column(ForeignKey("sensors.id"), nullable=True)
    alert_type_id: Mapped[int] = mapped_column(ForeignKey("alert_types.id"), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), CheckConstraint("severity IN ('low', 'medium', 'high', 'critical')", name="chk_alert_f98914"), nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float, CheckConstraint("confidence_score >= 0.0 AND confidence_score <= 1.0", name="chk_alert_85448e"), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_snapshot: Mapped[dict] = mapped_column(JSONB, server_default='{}', nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

Index("idx_alerts_active", Alert.device_id, postgresql_where=(Alert.is_resolved == False))
Index("idx_alerts_payload", Alert.payload_snapshot, postgresql_using="gin")
