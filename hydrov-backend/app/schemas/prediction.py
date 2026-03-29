# app/schemas/prediction.py
"""
Schemas Pydantic para los endpoints de predicción ML.

Endpoints que los usan:
  GET  /api/v1/predictions/{node_id}/autonomy
  GET  /api/v1/predictions/{node_id}/leaks
  GET  /api/v1/predictions/{node_id}/full
  GET  /api/v1/predictions/network-health  (futuro)
"""
from pydantic import BaseModel, Field, computed_field
from datetime import datetime, timezone
from typing import Optional


# ─────────────────────────────────────────────────────────────────
#  Autonomía Hídrica
# ─────────────────────────────────────────────────────────────────

class AutonomyPredictionResponseSchema(BaseModel):
    """
    Respuesta del endpoint GET /predictions/{node_id}/autonomy
    Retornada al frontend y al dashboard de Grafana.
    """
    node_id:            str
    days_autonomy:      float   = Field(description="Días estimados de agua disponible")
    confidence:         float   = Field(ge=0.0, le=1.0, description="Confianza del modelo (0-1)")
    alert:              bool    = Field(description="True si autonomía < 3 días")
    level_pct:          float   = Field(description="Nivel actual de cisterna en %")
    forecast_precip_mm: float   = Field(description="Precipitación pronosticada 72h (NASA POWER)")
    generated_at:       datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"from_attributes": True}


class AutonomyPredictionDBSchema(BaseModel):
    """
    Schema interno para persistir la predicción en PostgreSQL.
    Contiene todas las features usadas (auditoría + reentrenamiento futuro).
    """
    node_id:             str
    days_autonomy:       float
    confidence:          float
    alert:               bool
    level_pct:           float
    avg_consumption_lpd: float
    forecast_precip_mm:  float
    temperature_c:       float
    humidity_pct:        float
    days_without_rain:   int
    month:               int
    model_version:       str = "v1-baseline"

    model_config = {"from_attributes": True}


class AutonomyPredictionListSchema(BaseModel):
    """
    Respuesta del endpoint GET /predictions/{node_id}/autonomy/history
    Historial paginado de predicciones.
    """
    total: int
    items: list[AutonomyPredictionResponseSchema]


# ─────────────────────────────────────────────────────────────────
#  Detección de Fugas
# ─────────────────────────────────────────────────────────────────

class LeakDetectionResponseSchema(BaseModel):
    """
    Respuesta del endpoint GET /predictions/{node_id}/leaks
    """
    node_id:       str
    leak_detected: bool
    anomaly_score: float = Field(ge=0.0, le=1.0)
    confidence:    float = Field(ge=0.0, le=1.0)
    detected_at:   datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @computed_field
    @property
    def severity(self) -> Optional[str]:
        """
        Severidad calculada en base al anomaly_score.
        Coincide con las categorías del dashboard Network Intelligence.
        """
        if not self.leak_detected:
            return None
        if self.anomaly_score >= 0.95:
            return "CRÍTICA"
        if self.anomaly_score >= 0.85:
            return "ALTA"
        return "MEDIA"

    model_config = {"from_attributes": True}


class LeakDetectionListSchema(BaseModel):
    """
    Respuesta del endpoint GET /predictions/network/leaks
    Escaneo de todos los nodos activos de la red.
    """
    total_nodes:    int
    leaks_detected: int
    results:        list[LeakDetectionResponseSchema]
    scanned_at:     datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LeakDetectionDBSchema(BaseModel):
    """
    Schema interno para persistir la detección en PostgreSQL.
    Solo se guarda cuando anomaly_score >= 0.75.
    """
    node_id:       str
    anomaly_score: float
    leak_detected: bool
    confidence:    float
    flow_lpm:      float
    level_pct:     float
    model_version: str = "v1-mlp-baseline"

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────
#  Schema combinado — endpoint /full y dashboard
# ─────────────────────────────────────────────────────────────────

class FullPredictionResponseSchema(BaseModel):
    """
    Respuesta del endpoint GET /predictions/{node_id}/full
    Combina autonomía + fugas en una sola llamada.
    Usado por el widget de estado del dashboard.
    """
    node_id:  str
    autonomy: AutonomyPredictionResponseSchema
    leaks:    LeakDetectionResponseSchema


class NetworkHealthSchema(BaseModel):
    """
    Resumen ejecutivo del estado de toda la red.
    Retornado por GET /predictions/network-health
    Diseñado para el Stat panel superior del Mission Control de Grafana.
    """
    total_nodes:       int
    nodes_online:      int
    nodes_with_leaks:  int
    avg_autonomy_days: float
    critical_alerts:   int
    scanned_at:        datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
