"""leak_detection ORM model — Hydro-V"""
from sqlalchemy import Integer, String, Float, DateTime, ForeignKey, Boolean, CheckConstraint
from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.db.base import Base
from datetime import datetime


class LeakDetection(Base):
    """
    Resultado de inferencia del modelo GNN GraphSAGE (HydroGNN).
    Cada fila = una predicción de fuga emitida para un nodo en un instante.
    Referenciada en los dashboards hydrov_network_intelligence y en las
    reglas de alerting de Grafana.
    """
    __tablename__ = "leak_detections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Duplicado desnormalizado para queries de Grafana sin JOIN
    node_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    anomaly_score: Mapped[float] = mapped_column(
        Float,
        CheckConstraint("anomaly_score >= 0.0 AND anomaly_score <= 1.0", name="ck_leak_detections_score_range"),
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(String(20), nullable=False, server_default="medium")
    model_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    neighbor_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload_snapshot: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relación inversa con Device
    device: Mapped["Device"] = relationship("Device", back_populates="leak_detections")  # type: ignore[name-defined]
