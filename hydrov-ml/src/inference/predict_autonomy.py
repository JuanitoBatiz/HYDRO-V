# hydrov-ml/src/inference/predict_autonomy.py
import pickle
import numpy as np
from pathlib import Path

MODEL_PATH = Path(__file__).parent.parent.parent / "models" / "linear_autonomy.pkl"


def load_model():
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)


# Modelo cargado una sola vez al importar el módulo
_model = load_model()


def predict_autonomy(
    level_pct:          float,   # Nivel actual de cisterna en %
    avg_consumption_lpd: float,  # Consumo promedio litros/día últimos 7 días
    forecast_precip_mm: float,   # Precipitación pronosticada próximas 72h (NASA POWER)
    temperature_c:      float,   # Temperatura actual (NASA POWER)
    humidity_pct:       float,   # Humedad relativa (NASA POWER)
    days_without_rain:  int,     # Días consecutivos sin lluvia
    month:              int,     # Mes actual (1-12) para calibración estacional
) -> dict:
    """
    Predice los días de autonomía hídrica del nodo.

    Retorna:
        {
            "days_autonomy": float,   # días estimados de agua disponible
            "confidence":    float,   # 0.0 a 1.0
            "alert":         bool,    # True si autonomía < 3 días
        }
    """
    features = np.array([[
        level_pct,
        avg_consumption_lpd,
        forecast_precip_mm,
        temperature_c,
        humidity_pct,
        days_without_rain,
        month,
    ]])

    days = float(_model.predict(features)[0])
    days = max(0.0, days)  # nunca negativo

    return {
        "days_autonomy": round(days, 1),
        "confidence":    0.85,        # placeholder hasta tener métricas reales
        "alert":         days < 3.0,
    }