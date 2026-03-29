# app/models/prediction.py
"""
Modelos ORM para persistencia de resultados ML.

autonomy_predictions — resultados del modelo LinearRegression
leak_detections      — resultados del modelo GNN/MLP de fugas
"""
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import Base


class AutonomyPrediction(Base):
    """
    Registro de cada predicción de días de autonomía hídrica.
    Escrito por:
      - APScheduler (cada hora por nodo)
      - Endpoint POST /api/v1/predictions/{node_id}/autonomy
    Leído por:
      - Panel 12 del dashboard Mission Control (Grafana)
    """
    __tablename__ = "autonomy_predictions"

    id:      Mapped[int]  = mapped_column(Integer, primary_key=True, index=True)
    node_id: Mapped[str]  = mapped_column(
        String(50),
        ForeignKey("devices.device_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    # Features de entrada (para auditoría y reentrenamiento futuro)
    level_pct:           Mapped[float] = mapped_column(Float, nullable=False)
    avg_consumption_lpd: Mapped[float] = mapped_column(Float, nullable=False)
    forecast_precip_mm:  Mapped[float] = mapped_column(Float, nullable=False)
    temperature_c:       Mapped[float] = mapped_column(Float, nullable=False)
    humidity_pct:        Mapped[float] = mapped_column(Float, nullable=False)
    days_without_rain:   Mapped[int]   = mapped_column(Integer, nullable=False)
    month:               Mapped[int]   = mapped_column(Integer, nullable=False)

    # Resultado del modelo
    days_autonomy: Mapped[float] = mapped_column(Float, nullable=False)
    confidence:    Mapped[float] = mapped_column(Float, nullable=False, default=0.85)
    alert:         Mapped[bool]  = mapped_column(Boolean, nullable=False, default=False)
    model_version: Mapped[str]   = mapped_column(String(50), nullable=False, default="v1-baseline")

    # Relación ORM
    device = relationship("Device", back_populates="autonomy_predictions")


class LeakDetection(Base):
    """
    Registro de cada detección del modelo GNN/MLP de anomalías de flujo.
    Solo se persiste cuando anomaly_score >= 0.75.
    Escrito por:
      - Endpoint GET /api/v1/predictions/{node_id}/leaks
    Leído por:
      - Dashboard Network Intelligence (Grafana)
    """
    __tablename__ = "leak_detections"

    id:      Mapped[int]  = mapped_column(Integer, primary_key=True, index=True)
    node_id: Mapped[str]  = mapped_column(
        String(50),
        ForeignKey("devices.device_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    # Features usadas por el modelo
    flow_lpm:   Mapped[float] = mapped_column(Float, nullable=False)
    level_pct:  Mapped[float] = mapped_column(Float, nullable=False)

    # Resultado del modelo
    anomaly_score: Mapped[float] = mapped_column(Float, nullable=False)
    leak_detected: Mapped[bool]  = mapped_column(Boolean, nullable=False)
    confidence:    Mapped[float] = mapped_column(Float, nullable=False, default=0.80)

    # Datos de nodos vecinos (lista JSON — vacío si nodo único)
    neighbor_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)

    # Resolución manual (operador puede marcar como falso positivo)
    resolved:       Mapped[bool]           = mapped_column(Boolean, nullable=False, default=False)
    resolved_notes: Mapped[str | None]     = mapped_column(Text, nullable=True)
    resolved_at:    Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    model_version: Mapped[str] = mapped_column(String(50), nullable=False, default="v1-mlp-baseline")

    # Relación ORM
    device = relationship("Device", back_populates="leak_detections")
