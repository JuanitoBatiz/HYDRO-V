from sqlalchemy import BigInteger, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from datetime import datetime
from sqlalchemy.sql import func

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id"), nullable=True, index=True)
    valve_id: Mapped[int | None] = mapped_column(ForeignKey("valves.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    payload_json: Mapped[dict] = mapped_column(JSONB, server_default='{}', nullable=False)
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

Index("idx_audit_payload", AuditLog.payload_json, postgresql_using="gin")
