# ============================================================
#  Hydro-V · Inferencia — Predicción de Autonomía Hídrica
#  Archivo: src/inference/predict_autonomy.py
# ============================================================

from __future__ import annotations

import pickle
import numpy as np
from dataclasses import dataclass
from datetime import datetime, timedelta

from src.models.linear_autonomy import AutonomyPredictor

MODEL_PATH = "models/linear_autonomy.pkl"


@dataclass
class PrediccionAutonomia:
    """Resultado de la predicción de autonomía para un nodo."""
    device_id: str
    dias_restantes: float
    fecha_proxima_recarga: str   # ISO 8601
    confianza: float
    nivel_actual_litros: float


class AutonomyInference:
    """
    Carga el modelo de regresión lineal y predice días de autonomía.

    Uso:
        predictor = AutonomyInference()
        resultado = predictor.predecir(
            device_id="HYDRO-V-001",
            nivel_actual_litros=550.0,
            consumo_7d_lpm=2.3,
            consumo_30d_lpm=2.1,
            precipitacion_mm=0.0,
        )
    """

    def __init__(self, model_path: str = MODEL_PATH) -> None:
        self.predictor = AutonomyPredictor.load(model_path)

    def predecir(
        self,
        device_id: str,
        nivel_actual_litros: float,
        consumo_7d_lpm: float,
        consumo_30d_lpm: float,
        precipitacion_mm: float = 0.0,
    ) -> PrediccionAutonomia:
        """
        Predice cuántos días de agua quedan en la cisterna.

        Args:
            device_id            : ID del dispositivo (ej. "HYDRO-V-001").
            nivel_actual_litros  : Litros actuales en la cisterna.
            consumo_7d_lpm       : Promedio de consumo últimos 7 días (L/min).
            consumo_30d_lpm      : Promedio de consumo últimos 30 días (L/min).
            precipitacion_mm     : Lluvia pronosticada (mm) — de NASA POWER API.

        Returns:
            PrediccionAutonomia con días restantes y fecha estimada.
        """
        ahora = datetime.utcnow()
        X = np.array([[
            nivel_actual_litros,
            consumo_7d_lpm,
            consumo_30d_lpm,
            precipitacion_mm,
            ahora.weekday(),   # 0=lunes … 6=domingo
            ahora.month,
        ]])

        dias = float(self.predictor.predict(X)[0])
        fecha_recarga = (ahora + timedelta(days=dias)).date().isoformat()

        return PrediccionAutonomia(
            device_id=device_id,
            dias_restantes=round(dias, 2),
            fecha_proxima_recarga=fecha_recarga,
            confianza=0.89,   # Actualizar con R² real tras entrenar
            nivel_actual_litros=nivel_actual_litros,
        )