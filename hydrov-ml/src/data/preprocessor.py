# ============================================================
#  Hydro-V · Capa de Datos — Preprocesamiento
#  Archivo: src/data/preprocessor.py
# ============================================================
#
#  Centraliza toda la lógica de preprocesamiento:
#    - Normalización de telemetría a [0, 1]
#    - Construcción de feature vectors para cada modelo
#    - Codificación cíclica de tiempo (hora/día/mes)
#    - Detección y limpieza de valores anómalos en sensores
#
#  Diseñado para ser usado tanto por los scripts de
#  entrenamiento como por las funciones de inferencia,
#  garantizando que ambos usen exactamente la misma
#  transformación de datos.
# ============================================================

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Optional


# ─────────────────────────────────────────────────────────────
#  Constantes físicas del sistema HYDRO-V
# ─────────────────────────────────────────────────────────────

# Rangos de sensores (límites físicos del hardware)
TURBIDEZ_MAX_NTU   = 1_000.0   # Sensor analógico: ADC 12-bit → NTU
FLUJO_MAX_LPM      = 30.0      # YF-S201: máximo operativo
DISTANCIA_MAX_CM   = 500.0     # HC-SR04 / JSN-SR04T: rango máximo
FLUJO_TOTAL_REF    = 10_000.0  # Referencia para normalizar el acumulado

# Parámetros de la cisterna
CISTERNA_LITROS    = 1_000.0   # Capacidad típica (litros)
ROOF_AREA_M2       = 45.0      # Área de captación (m²)
COLLECT_EFF        = 0.85      # Eficiencia de captación pluvial

# Umbrales físicos de la FSM del ESP32
FSM_UMBRAL_TURBIDEZ_NTU  = 122.0   # 500 ADC ≈ 122 NTU → REJECT
FSM_UMBRAL_DISTANCIA_CM  = 100.0   # cisterna "vacía" → INTAKE

# Rangos de features del modelo de autonomía
LEVEL_NORM_MAX        = 100.0
CONSUMPTION_NORM_REF  = 500.0   # L/día máximo realista


# ═══════════════════════════════════════════════════════════════
#  Normalización de telemetría
# ═══════════════════════════════════════════════════════════════

def normalize_telemetry(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza las columnas de sensores de un DataFrame de telemetría
    a rango [0, 1] usando los rangos físicos reales del hardware.

    Columnas normalizadas (si existen en el DataFrame):
        turbidity_ntu  → turbidity_norm
        flow_lpm       → flow_norm
        distance_cm    → distance_norm
        flow_total     → flow_total_norm

    Las columnas cíclicas (hora_sin, hora_cos, etc.) ya están en [-1, 1];
    se copian sin cambios.

    Args:
        df: DataFrame de telemetría (salida de loader.load_telemetry_csv
            o de synthetic_generator.generar_datos_nodo).

    Returns:
        Nuevo DataFrame con columnas _norm añadidas. El original no se modifica.
    """
    out = df.copy()

    if "turbidity_ntu" in out.columns:
        out["turbidity_norm"] = (out["turbidity_ntu"] / TURBIDEZ_MAX_NTU).clip(0.0, 1.0)

    if "flow_lpm" in out.columns:
        out["flow_norm"] = (out["flow_lpm"] / FLUJO_MAX_LPM).clip(0.0, 1.0)

    if "distance_cm" in out.columns:
        out["distance_norm"] = (out["distance_cm"] / DISTANCIA_MAX_CM).clip(0.0, 1.0)

    if "flow_total" in out.columns:
        ref = max(float(out["flow_total"].max()), 1.0)
        out["flow_total_norm"] = (out["flow_total"] / ref).clip(0.0, 1.0)

    return out


# ═══════════════════════════════════════════════════════════════
#  Feature engineering por modelo
# ═══════════════════════════════════════════════════════════════

def build_autonomy_features(
    level_pct:           float,
    avg_consumption_lpd: float,
    forecast_precip_mm:  float,
    temperature_c:       float,
    humidity_pct:        float,
    days_without_rain:   int,
    month:               int,
) -> np.ndarray:
    """
    Construye el vector de 7 features para el modelo de autonomía.

    Debe coincidir exactamente con las columnas usadas en el
    entrenamiento (generate_synthetic_data.py → generate_autonomy_data).

    Orden de features:
        [0] level_pct           — nivel de cisterna (0–100)
        [1] avg_consumption_lpd — consumo promedio diario (L/día)
        [2] forecast_precip_mm  — precipitación pronosticada 72h (mm)
        [3] temperature_c       — temperatura promedio (°C)
        [4] humidity_pct        — humedad relativa (%)
        [5] days_without_rain   — días secos consecutivos
        [6] month               — mes del año (1–12)

    Returns:
        np.ndarray de shape [1, 7] listo para pipeline.predict()
    """
    return np.array([[
        float(level_pct),
        float(avg_consumption_lpd),
        float(forecast_precip_mm),
        float(temperature_c),
        float(humidity_pct),
        float(days_without_rain),
        float(month),
    ]], dtype=np.float64)


def build_leak_features(
    flow_lpm:        float,
    level_pct:       float,
    neighbor_flows:  list[float],
    neighbor_levels: list[float],
) -> np.ndarray:
    """
    Construye el vector de 10 features para LeakDetectorMLP.

    Diseñado para capturar tanto el estado del nodo como
    su relación con los vecinos hidráulicos.

    Orden de features (LeakDetectorMLP.MAX_INPUT_DIM = 10):
        [0] flow_norm              — flujo del nodo ∈ [0, 1]
        [1] level_norm             — nivel del nodo ∈ [0, 1]
        [2] avg_n_flow_norm        — flujo medio vecinos ∈ [0, 1]
        [3] avg_n_level_norm       — nivel medio vecinos ∈ [0, 1]
        [4] flow_deviation         — |flujo_nodo − flujo_vecinos|
        [5] level_deviation        — |nivel_nodo − nivel_vecinos|
        [6] is_low_level           — 1 si nivel < 20 %
        [7] is_high_flow_low_level — 1 si flujo > 4 LPM y nivel < 40 %
        [8] pad_0                  — reservado (0.0)
        [9] pad_1                  — reservado (0.0)

    Args:
        flow_lpm        : Flujo instantáneo del nodo (L/min).
        level_pct       : Nivel de cisterna del nodo (0–100 %).
        neighbor_flows  : Flujos de los nodos vecinos.
        neighbor_levels : Niveles de los nodos vecinos.

    Returns:
        np.ndarray de shape [1, 10] listo para LeakDetectorMLP.
    """
    avg_n_flow  = float(np.mean(neighbor_flows))  if neighbor_flows  else flow_lpm
    avg_n_level = float(np.mean(neighbor_levels)) if neighbor_levels else level_pct

    flow_norm        = min(flow_lpm  / FLUJO_MAX_LPM,   1.0)
    level_norm       = min(level_pct / LEVEL_NORM_MAX,  1.0)
    avg_n_flow_norm  = min(avg_n_flow  / FLUJO_MAX_LPM,  1.0)
    avg_n_level_norm = min(avg_n_level / LEVEL_NORM_MAX, 1.0)

    flow_dev   = abs(flow_norm  - avg_n_flow_norm)
    level_dev  = abs(level_norm - avg_n_level_norm)
    is_low     = 1.0 if level_pct < 20.0                          else 0.0
    is_hf_ll   = 1.0 if (flow_lpm > 4.0 and level_pct < 40.0)    else 0.0

    return np.array(
        [[flow_norm, level_norm, avg_n_flow_norm, avg_n_level_norm,
          flow_dev, level_dev, is_low, is_hf_ll, 0.0, 0.0]],
        dtype=np.float32,
    )


# ═══════════════════════════════════════════════════════════════
#  Codificación cíclica del tiempo
# ═══════════════════════════════════════════════════════════════

def encode_hour(hour: float) -> tuple[float, float]:
    """
    Codificación cíclica de la hora del día (0–23).

    Retorna (sin, cos) para que el modelo trate 23h y 0h como cercanas.
    """
    angle = 2.0 * np.pi * hour / 24.0
    return float(np.sin(angle)), float(np.cos(angle))


def encode_day_of_week(day: int) -> tuple[float, float]:
    """
    Codificación cíclica del día de la semana (0=lunes, 6=domingo).
    """
    angle = 2.0 * np.pi * day / 7.0
    return float(np.sin(angle)), float(np.cos(angle))


def encode_month(month: int) -> tuple[float, float]:
    """
    Codificación cíclica del mes (1–12).
    """
    angle = 2.0 * np.pi * (month - 1) / 12.0
    return float(np.sin(angle)), float(np.cos(angle))


def add_time_features(df: pd.DataFrame, timestamp_col: str = "timestamp") -> pd.DataFrame:
    """
    Agrega columnas de tiempo cíclico a un DataFrame de telemetría.

    Columnas añadidas: hora_sin, hora_cos, dia_sin, dia_cos, mes_sin, mes_cos

    Args:
        df            : DataFrame con columna de timestamps.
        timestamp_col : Nombre de la columna de timestamp.

    Returns:
        DataFrame con columnas de tiempo añadidas.
    """
    if timestamp_col not in df.columns:
        raise ValueError(f"[preprocessor] Columna '{timestamp_col}' no encontrada.")

    ts = pd.to_datetime(df[timestamp_col])
    out = df.copy()

    horas      = ts.dt.hour + ts.dt.minute / 60.0
    dias       = ts.dt.dayofweek.astype(float)
    meses      = ts.dt.month.astype(float)

    out["hora_sin"] = np.sin(2 * np.pi * horas / 24.0)
    out["hora_cos"] = np.cos(2 * np.pi * horas / 24.0)
    out["dia_sin"]  = np.sin(2 * np.pi * dias  / 7.0)
    out["dia_cos"]  = np.cos(2 * np.pi * dias  / 7.0)
    out["mes_sin"]  = np.sin(2 * np.pi * (meses - 1) / 12.0)
    out["mes_cos"]  = np.cos(2 * np.pi * (meses - 1) / 12.0)

    return out


# ═══════════════════════════════════════════════════════════════
#  Limpieza y validación
# ═══════════════════════════════════════════════════════════════

def clean_sensor_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Elimina o reemplaza lecturas de sensores físicamente imposibles.

    Reglas aplicadas:
      - turbidity_ntu  : clip a [0, TURBIDEZ_MAX_NTU]
      - flow_lpm       : clip a [0, FLUJO_MAX_LPM]
      - distance_cm    : clip a [0, DISTANCIA_MAX_CM]
        Nota: valores = 0 en ultrasónico suelen ser errores de timeout.

    Args:
        df: DataFrame de telemetría.

    Returns:
        DataFrame con outliers corregidos.
    """
    out = df.copy()

    if "turbidity_ntu" in out.columns:
        out["turbidity_ntu"] = out["turbidity_ntu"].clip(0.0, TURBIDEZ_MAX_NTU)

    if "flow_lpm" in out.columns:
        out["flow_lpm"] = out["flow_lpm"].clip(0.0, FLUJO_MAX_LPM)

    if "distance_cm" in out.columns:
        # Reemplazar 0.0 (timeout ultrasónico) con NaN para no confundir al modelo
        out["distance_cm"] = out["distance_cm"].replace(0.0, np.nan)
        out["distance_cm"] = out["distance_cm"].clip(0.0, DISTANCIA_MAX_CM)

    return out


def validate_autonomy_inputs(
    level_pct:           float,
    avg_consumption_lpd: float,
) -> list[str]:
    """
    Valida los inputs más críticos del modelo de autonomía.

    Returns:
        Lista de advertencias (vacía si todo está bien).
    """
    warnings = []
    if not (0.0 <= level_pct <= 100.0):
        warnings.append(f"level_pct={level_pct} fuera de rango [0, 100]")
    if avg_consumption_lpd <= 0.0:
        warnings.append(f"avg_consumption_lpd={avg_consumption_lpd} debe ser > 0")
    if avg_consumption_lpd > CONSUMPTION_NORM_REF:
        warnings.append(
            f"avg_consumption_lpd={avg_consumption_lpd} > {CONSUMPTION_NORM_REF} L/día — "
            "valor inusualmente alto, revisa la unidad (debe ser L/día, no L/min)"
        )
    return warnings


# ── Test rápido ───────────────────────────────────────────────
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

    print("=" * 55)
    print("🔧 HYDRO-V · Test preprocessor.py")
    print("=" * 55)

    # 1. build_autonomy_features
    X_auto = build_autonomy_features(
        level_pct=60.0, avg_consumption_lpd=150.0,
        forecast_precip_mm=5.0, temperature_c=20.0,
        humidity_pct=60.0, days_without_rain=3, month=7,
    )
    print(f"\nbuild_autonomy_features → shape={X_auto.shape}\n  {X_auto}")

    # 2. build_leak_features
    X_leak = build_leak_features(
        flow_lpm=7.5, level_pct=15.0,
        neighbor_flows=[1.0, 0.8], neighbor_levels=[70.0, 68.0],
    )
    print(f"\nbuild_leak_features → shape={X_leak.shape}\n  {X_leak}")

    # 3. encode_hour
    h_sin, h_cos = encode_hour(23.5)
    h_sin0, h_cos0 = encode_hour(0.0)
    print(f"\nencode_hour(23.5) = ({h_sin:.3f}, {h_cos:.3f})")
    print(f"encode_hour(0.0)  = ({h_sin0:.3f}, {h_cos0:.3f})  ← deben ser cercanos")

    # 4. normalize_telemetry
    df_raw = pd.DataFrame({
        "turbidity_ntu": [50.0, 500.0, 1100.0],
        "flow_lpm":      [2.0,  15.0,  35.0],
        "distance_cm":   [0.0,  100.0, 600.0],
    })
    df_norm = normalize_telemetry(df_raw)
    print(f"\nnormalize_telemetry:\n{df_norm[['turbidity_norm', 'flow_norm', 'distance_norm']]}")

    # 5. validate_autonomy_inputs
    warns = validate_autonomy_inputs(level_pct=110.0, avg_consumption_lpd=0.0)
    print(f"\nvalidate_autonomy_inputs(110, 0):\n  {warns}")
    ok = validate_autonomy_inputs(level_pct=60.0, avg_consumption_lpd=150.0)
    print(f"validate_autonomy_inputs(60, 150) → {'✓ sin advertencias' if not ok else ok}")

    print("\n✅ preprocessor.py funciona correctamente")
