# ============================================================
#  Hydro-V · Inferencia — Predicción de Autonomía Hídrica
#  Archivo: src/inference/predict_autonomy.py
# ============================================================
#
#  Expone DOS interfaces públicas:
#
#  1. predict_autonomy(level_pct, avg_consumption_lpd, ...) -> dict
#     ── Función de alto nivel que llama ml_service.py.
#        Retorna un dict con days_autonomy, confidence y alert.
#        Confianza calculada dinámicamente según la calidad
#        de los inputs y el margen de la predicción.
#
#  2. AutonomyInference (clase)
#     ── Para uso avanzado o scripts de entrenamiento.
#
#  Modelo soportado: sklearn Pipeline guardado con pickle
#  (generado por generate_synthetic_data.py → train_autonomy_model)
#  Fallback: modelo físico cuando no hay .pkl disponible.
# ============================================================

from __future__ import annotations

import pickle
import numpy as np
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from src.models.linear_autonomy import AutonomyPredictor


# ── Configuración ─────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent.parent.parent
MODEL_PATH = BASE_DIR / "models" / "linear_autonomy.pkl"

# Rangos válidos de entrada (para penalizar confianza si se exceden)
LEVEL_MIN, LEVEL_MAX          = 2.0,   100.0
CONSUMPTION_MIN, CONSUMPTION_MAX = 30.0, 500.0
DAYS_DRY_MAX                  = 30
DAYS_AUTONOMY_MAX             = 60.0   # máximo físico que reconocemos

# Umbrales de alerta (días de autonomía)
ALERT_CRITICAL = 2    # < 2 días  → crítico
ALERT_WARNING  = 7    # < 7 días  → advertencia


# ── Singleton del modelo ──────────────────────────────────────
_pipeline_cache = None


def _load_pipeline():
    """
    Carga el modelo de autonomía desde disco.
    Soporta dos formatos:
      - sklearn Pipeline (guardado con pickle por generate_synthetic_data.py)
      - Dict {"model": ..., "scaler": ...} (AutonomyPredictor.save())

    Retorna el objeto con método .predict(X) o None si no hay archivo.
    """
    global _pipeline_cache
    if _pipeline_cache is not None:
        return _pipeline_cache

    if not MODEL_PATH.exists():
        print(f"[AutonomyInference] ⚠️  Modelo no encontrado en {MODEL_PATH}. "
              "Usando modelo físico de fallback.")
        return None

    try:
        with open(MODEL_PATH, "rb") as f:
            datos = pickle.load(f)

        # Caso A: sklearn Pipeline completo (tiene .predict directamente)
        if hasattr(datos, "predict"):
            _pipeline_cache = datos
            print(f"[AutonomyInference] ✓ Pipeline sklearn cargado desde {MODEL_PATH}")
            return _pipeline_cache

        # Caso B: formato AutonomyPredictor {"model": ..., "scaler": ...}
        if isinstance(datos, dict) and "model" in datos:
            predictor          = AutonomyPredictor()
            predictor.model    = datos["model"]
            predictor.scaler   = datos["scaler"]
            predictor._is_fitted = True
            _pipeline_cache    = predictor
            print(f"[AutonomyInference] ✓ AutonomyPredictor cargado desde {MODEL_PATH}")
            return _pipeline_cache

    except Exception as exc:
        print(f"[AutonomyInference] ⚠️  Error al cargar modelo: {exc}. Usando físico.")

    return None


# ── Constructor de features ───────────────────────────────────
# El modelo fue entrenado con estas 7 columnas (en este orden):
#   level_pct, avg_consumption_lpd, forecast_precip_mm,
#   temperature_c, humidity_pct, days_without_rain, month

def _build_features(
    level_pct:           float,
    avg_consumption_lpd: float,
    forecast_precip_mm:  float,
    temperature_c:       float,
    humidity_pct:        float,
    days_without_rain:   int,
    month:               int,
) -> np.ndarray:
    return np.array([[
        level_pct,
        avg_consumption_lpd,
        forecast_precip_mm,
        temperature_c,
        humidity_pct,
        float(days_without_rain),
        float(month),
    ]], dtype=np.float64)


# ── Cálculo de confianza ──────────────────────────────────────

def _compute_confidence(
    level_pct:           float,
    avg_consumption_lpd: float,
    forecast_precip_mm:  float,
    days_without_rain:   int,
    days_autonomy:       float,
    has_trained_model:   bool,
) -> float:
    """
    Calcula la confianza de la predicción de forma dinámica.

    Base:
      - Modelo entrenado → 0.90  (R² ≈ 0.87–0.93 en validación cruzada)
      - Modelo físico    → 0.70  (heurística, menos precisa)

    Penalizaciones (cada una es independiente):
      - Inputs fuera de rango realista        → −0.05 a −0.10
      - Predicción en extremos (< 0.5 d o > 45 d) → −0.07
      - Sequía prolongada (> 25 días)         → −0.05
        (el modelo fue entrenado con máx. ~30 días secos)
    """
    confidence = 0.90 if has_trained_model else 0.70

    # Penalización por inputs anómalos
    if not (LEVEL_MIN <= level_pct <= LEVEL_MAX):
        confidence -= 0.08
    if not (CONSUMPTION_MIN <= avg_consumption_lpd <= CONSUMPTION_MAX):
        confidence -= 0.08
    if avg_consumption_lpd < 50.0:
        confidence -= 0.05
    if days_without_rain > 25:
        confidence -= 0.05
    if forecast_precip_mm > 60.0:
        confidence -= 0.04   # lluvia extrema → alta incertidumbre

    # Penalización por predicción en los bordes
    if days_autonomy < 0.5 or days_autonomy > 45.0:
        confidence -= 0.07

    return round(float(np.clip(confidence, 0.40, 0.99)), 2)


# ── Reglas de alerta ──────────────────────────────────────────

def _compute_alert(days_autonomy: float) -> str:
    """
    Devuelve el nivel de alerta en función de los días de autonomía.
      "critical" → < 2 días  (acción inmediata)
      "warning"  → < 7 días  (planificar recarga)
      "ok"       → ≥ 7 días  (todo en orden)
    """
    if days_autonomy < ALERT_CRITICAL:
        return "critical"
    if days_autonomy < ALERT_WARNING:
        return "warning"
    return "ok"


# ══════════════════════════════════════════════════════════════
#  FUNCIÓN PÚBLICA PRINCIPAL — usada por ml_service.py
# ══════════════════════════════════════════════════════════════

def predict_autonomy(
    level_pct:           float,
    avg_consumption_lpd: float,
    forecast_precip_mm:  float  = 0.0,
    temperature_c:       float  = 20.0,
    humidity_pct:        float  = 50.0,
    days_without_rain:   int    = 0,
    month:               int    = 1,
) -> dict:
    """
    Predice los días de autonomía hídrica de un nodo.

    Acepta los datos procesados del nodo y contexto climático.
    ml_service.py ya se encargó de obtener el consumo promedio
    desde InfluxDB y los datos NASA POWER — aquí solo predecimos.

    Args:
        level_pct           : Nivel de cisterna (0–100 %).
        avg_consumption_lpd : Consumo promedio diario (L/día).
        forecast_precip_mm  : Precipitación pronosticada en 72h (mm).
        temperature_c       : Temperatura promedio (°C).
        humidity_pct        : Humedad relativa (%).
        days_without_rain   : Días sin lluvia hasta hoy.
        month               : Mes del año (1–12).

    Returns:
        dict con claves:
            days_autonomy    (float) — días estimados de agua restante
            confidence       (float) — confianza de la predicción [0–1]
            alert            (str)   — "ok" | "warning" | "critical"
            estimated_date   (str)   — fecha estimada de agotamiento (ISO)
    """
    pipeline          = _load_pipeline()
    has_trained_model = pipeline is not None

    if has_trained_model:
        X      = _build_features(
            level_pct, avg_consumption_lpd, forecast_precip_mm,
            temperature_c, humidity_pct, days_without_rain, month,
        )
        raw    = float(pipeline.predict(X)[0])
        days   = round(float(np.clip(raw, 0.0, DAYS_AUTONOMY_MAX)), 2)
    else:
        # Modelo físico: volumen_disponible / consumo + aporte lluvia
        cisterna_litros = 1_000.0
        roof_area_m2    = 45.0
        collect_eff     = 0.85

        vol_actual = (level_pct / 100.0) * cisterna_litros
        aporte     = forecast_precip_mm * roof_area_m2 * collect_eff
        vol_total  = vol_actual + aporte

        raw  = vol_total / max(avg_consumption_lpd, 1.0)
        days = round(float(np.clip(raw, 0.0, DAYS_AUTONOMY_MAX)), 2)

    confidence     = _compute_confidence(
        level_pct, avg_consumption_lpd, forecast_precip_mm,
        days_without_rain, days, has_trained_model,
    )
    alert          = _compute_alert(days)
    estimated_date = (
        datetime.now(timezone.utc) + timedelta(days=days)
    ).date().isoformat()

    return {
        "days_autonomy":  days,
        "confidence":     confidence,
        "alert":          alert,
        "estimated_date": estimated_date,
    }


# ══════════════════════════════════════════════════════════════
#  CLASE AutonomyInference — para uso avanzado / scripts
# ══════════════════════════════════════════════════════════════

@dataclass
class PrediccionAutonomia:
    device_id:            str
    dias_restantes:       float
    fecha_proxima_recarga: str
    confianza:            float
    nivel_actual_litros:  float
    alerta:               str


class AutonomyInference:
    """
    Wrapper orientado a objetos para el modelo de autonomía.

    Útil en scripts de batch prediction o cuando se requiere
    el resultado como dataclass tipado.
    """

    def __init__(self, model_path: Path = MODEL_PATH) -> None:
        self.predictor = AutonomyPredictor.load(str(model_path))

    def predecir(
        self,
        device_id:           str,
        nivel_actual_litros: float,
        consumo_7d_lpm:      float,
        consumo_30d_lpm:     float,
        precipitacion_mm:    float = 0.0,
    ) -> PrediccionAutonomia:
        ahora = datetime.now(timezone.utc)

        X = np.array([[
            nivel_actual_litros,
            consumo_7d_lpm,
            consumo_30d_lpm,
            precipitacion_mm,
            float(ahora.weekday()),
            float(ahora.month),
        ]])

        dias = float(self.predictor.predict(X)[0])
        dias = max(0.0, dias)

        return PrediccionAutonomia(
            device_id=device_id,
            dias_restantes=round(dias, 2),
            fecha_proxima_recarga=(ahora + timedelta(days=dias)).date().isoformat(),
            confianza=_compute_confidence(
                level_pct=nivel_actual_litros / 10.0,
                avg_consumption_lpd=consumo_7d_lpm * 1440,
                forecast_precip_mm=precipitacion_mm,
                days_without_rain=0,
                days_autonomy=dias,
                has_trained_model=self.predictor._is_fitted,
            ),
            nivel_actual_litros=nivel_actual_litros,
            alerta=_compute_alert(dias),
        )


# ── Test manual ───────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("🤖 HYDRO-V · Test predict_autonomy() (función pública)")
    print("=" * 55)

    casos = [
        dict(level_pct=50.0, avg_consumption_lpd=150.0, forecast_precip_mm=5.0,
             temperature_c=20.0, humidity_pct=60.0, days_without_rain=3,  month=6,
             desc="Situación media (temporada lluvias)"),
        dict(level_pct=90.0, avg_consumption_lpd=100.0, forecast_precip_mm=20.0,
             temperature_c=18.0, humidity_pct=75.0, days_without_rain=0,  month=8,
             desc="Cisterna llena + lluvia → óptimo"),
        dict(level_pct=10.0, avg_consumption_lpd=200.0, forecast_precip_mm=0.0,
             temperature_c=28.0, humidity_pct=40.0, days_without_rain=15, month=3,
             desc="Cisterna casi vacía, sequía → crítico"),
        dict(level_pct=35.0, avg_consumption_lpd=180.0, forecast_precip_mm=2.0,
             temperature_c=22.0, humidity_pct=55.0, days_without_rain=7,  month=11,
             desc="Temporada seca → advertencia"),
    ]

    for caso in casos:
        desc  = caso.pop("desc")
        res   = predict_autonomy(**caso)
        emoji = {"ok": "✅", "warning": "⚠️ ", "critical": "🚨"}[res["alert"]]
        print(
            f"\n{emoji} {desc}\n"
            f"   días={res['days_autonomy']:.1f}  "
            f"confianza={res['confidence']:.0%}  "
            f"alerta={res['alert']}  "
            f"hasta={res['estimated_date']}"
        )