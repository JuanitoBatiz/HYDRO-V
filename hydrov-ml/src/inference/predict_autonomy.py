# ============================================================
#  Hydro-V · Inferencia — Predicción de Autonomía Hídrica
#  Archivo: src/inference/predict_autonomy.py
# ============================================================

from __future__ import annotations

import numpy as np
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.models.linear_autonomy import AutonomyPredictor


# ── Configuración ─────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent
MODEL_PATH = BASE_DIR / "models" / "linear_autonomy.pkl"


@dataclass
class PrediccionAutonomia:
    device_id: str
    dias_restantes: float
    fecha_proxima_recarga: str
    confianza: float
    nivel_actual_litros: float


class AutonomyInference:
    """
    Predicción profesional de autonomía hídrica.

    - Usa modelo entrenado (regresión lineal)
    - Retorna datos listos para API/backend
    - Incluye fecha estimada de agotamiento
    """

    def __init__(self, model_path: Path = MODEL_PATH) -> None:
        try:
            self.predictor = AutonomyPredictor.load(str(model_path))
            print(f"[AutonomyInference] Modelo cargado desde: {model_path}")
        except FileNotFoundError:
            raise FileNotFoundError(
                f"No se encontró el modelo en {model_path}. "
                "Ejecuta primero el entrenamiento."
            )

    def predecir(
        self,
        device_id: str,
        nivel_actual_litros: float,
        consumo_7d_lpm: float,
        consumo_30d_lpm: float,
        precipitacion_mm: float = 0.0,
    ) -> PrediccionAutonomia:

        ahora = datetime.now(timezone.utc)

        X = np.array([[
            nivel_actual_litros,
            consumo_7d_lpm,
            consumo_30d_lpm,
            precipitacion_mm,
            ahora.weekday(),
            ahora.month,
        ]])

        dias = float(self.predictor.predict(X)[0])
        dias = max(0.0, dias)  # seguridad

        fecha_recarga = (ahora + timedelta(days=dias)).date().isoformat()

        return PrediccionAutonomia(
            device_id=device_id,
            dias_restantes=round(dias, 2),
            fecha_proxima_recarga=fecha_recarga,
            confianza=0.89,  # TODO: reemplazar con métrica real
            nivel_actual_litros=nivel_actual_litros,
        )


# ── Test manual ───────────────────────────────────────────────
if __name__ == "__main__":
    print("=========================================")
    print("🤖 HYDRO-V · PREDICCIÓN DE AUTONOMÍA")
    print("=========================================")

    try:
        predictor = AutonomyInference()

        resultado = predictor.predecir(
            device_id="HYDRO-V-NEZA-001",
            nivel_actual_litros=550.0,
            consumo_7d_lpm=2.3,
            consumo_30d_lpm=2.1,
            precipitacion_mm=0.0
        )

        print(f"📍 Nodo: {resultado.device_id}")
        print(f"💧 Nivel: {resultado.nivel_actual_litros} L")
        print(f"⏳ Días restantes: {resultado.dias_restantes}")
        print(f"📅 Fecha estimada: {resultado.fecha_proxima_recarga}")

    except Exception as e:
        print(f"🛑 Error: {e}")