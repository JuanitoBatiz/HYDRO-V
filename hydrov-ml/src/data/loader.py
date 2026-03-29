# ============================================================
#  Hydro-V · Capa de Datos — Carga de datos
#  Archivo: src/data/loader.py
# ============================================================
#
#  Centraliza la carga de datos desde distintas fuentes:
#    - CSV generados por generate_synthetic_data.py
#    - Resultados de queries InfluxDB (JSON / dicts)
#    - Modelos ML serializados (pkl / pth)
#
#  Todas las funciones retornan tipos concretos y loguean
#  un resumen para facilitar el debugging.
# ============================================================

from __future__ import annotations

import pickle
import logging
from pathlib import Path
from typing import Optional, Union

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

log = logging.getLogger(__name__)


# ── Constantes ────────────────────────────────────────────────
# Columnas esperadas en el CSV de telemetría sintética
TELEMETRY_COLS = [
    "device_id", "timestamp",
    "turbidity_ntu", "flow_lpm", "distance_cm", "flow_total",
    "hora_sin", "hora_cos", "dia_sin", "dia_cos", "label",
]

# Columnas esperadas en el CSV de autonomía
AUTONOMY_COLS = [
    "level_pct", "avg_consumption_lpd", "forecast_precip_mm",
    "temperature_c", "humidity_pct", "days_without_rain", "month",
    "days_autonomy",
]

# ═══════════════════════════════════════════════════════════════
#  Carga de DataFrames
# ═══════════════════════════════════════════════════════════════

def load_telemetry_csv(path: Union[str, Path]) -> pd.DataFrame:
    """
    Carga un CSV de telemetría sintética generado por
    synthetic_generator.py o generate_synthetic_data.py.

    Args:
        path: Ruta al archivo CSV.

    Returns:
        DataFrame con columnas TELEMETRY_COLS tipadas correctamente.

    Raises:
        FileNotFoundError: Si el archivo no existe.
        ValueError:        Si faltan columnas obligatorias.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"[loader] Archivo no encontrado: {path}")

    df = pd.read_csv(path, parse_dates=["timestamp"])

    # Verificar columnas mínimas
    required = {"device_id", "timestamp", "turbidity_ntu", "flow_lpm"}
    missing  = required - set(df.columns)
    if missing:
        raise ValueError(f"[loader] Columnas faltantes en {path.name}: {missing}")

    # Asegurar tipos
    df["device_id"]     = df["device_id"].astype(str)
    df["turbidity_ntu"] = pd.to_numeric(df["turbidity_ntu"], errors="coerce").fillna(0.0)
    df["flow_lpm"]      = pd.to_numeric(df["flow_lpm"],      errors="coerce").fillna(0.0)
    df["distance_cm"]   = pd.to_numeric(df.get("distance_cm", 0.0), errors="coerce").fillna(0.0)

    if "label" in df.columns:
        df["label"] = df["label"].astype(int)

    log.info(
        "[loader] Telemetría cargada: %d filas, %d dispositivos desde %s",
        len(df), df["device_id"].nunique(), path.name,
    )
    return df


def load_autonomy_csv(path: Union[str, Path]) -> tuple[np.ndarray, np.ndarray]:
    """
    Carga el CSV de datos de autonomía y retorna (X, y) listos
    para entrenar el modelo de sklearn.

    Args:
        path: Ruta al CSV generado por generate_synthetic_data.py.

    Returns:
        X : np.ndarray de shape [n_samples, 7]
        y : np.ndarray de shape [n_samples] — días de autonomía
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"[loader] Archivo no encontrado: {path}")

    df = pd.read_csv(path)

    feature_cols = [c for c in AUTONOMY_COLS if c != "days_autonomy"]
    missing      = set(feature_cols + ["days_autonomy"]) - set(df.columns)
    if missing:
        raise ValueError(f"[loader] Columnas faltantes: {missing}")

    X = df[feature_cols].to_numpy(dtype=np.float64)
    y = df["days_autonomy"].to_numpy(dtype=np.float64)

    log.info("[loader] Autonomía: X=%s  y=%s desde %s", X.shape, y.shape, path.name)
    return X, y


def load_influx_result(
    records: list[dict],
    *,
    node_id_key:  str = "node_id",
    timestamp_key: str = "_time",
) -> pd.DataFrame:
    """
    Convierte el resultado de una query InfluxDB (lista de dicts)
    en un DataFrame normalizado.

    Args:
        records       : Lista de registros retornados por InfluxDB client.
        node_id_key   : Nombre del tag que identifica el nodo.
        timestamp_key : Nombre del campo de tiempo.

    Returns:
        DataFrame con columnas: timestamp, device_id, + campos de medición.
    """
    if not records:
        log.warning("[loader] load_influx_result: lista vacía recibida.")
        return pd.DataFrame()

    df = pd.DataFrame(records)

    # Renombrar columnas estándar
    renames = {}
    if timestamp_key in df.columns:
        renames[timestamp_key] = "timestamp"
    if node_id_key in df.columns:
        renames[node_id_key] = "device_id"
    if renames:
        df = df.rename(columns=renames)

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

    log.info("[loader] InfluxDB result: %d registros cargados.", len(df))
    return df


# ═══════════════════════════════════════════════════════════════
#  Carga de modelos ML
# ═══════════════════════════════════════════════════════════════

def load_model_pkl(path: Union[str, Path]) -> Optional[object]:
    """
    Carga de forma segura un modelo serializado con pickle.
    Devuelve el objeto cargado o None si el archivo no existe.

    Soporta:
      - sklearn Pipeline (generate_synthetic_data.py)
      - AutonomyPredictor dict {"model": ..., "scaler": ...}
      - Cualquier otro objeto serializable con pickle

    Args:
        path: Ruta al archivo .pkl

    Returns:
        El objeto deserializado, o None si no existe / falla.
    """
    path = Path(path)
    if not path.exists():
        log.warning("[loader] Modelo PKL no encontrado: %s", path)
        return None

    try:
        with open(path, "rb") as f:
            modelo = pickle.load(f)
        log.info("[loader] Modelo PKL cargado: %s (%s)", path.name, type(modelo).__name__)
        return modelo
    except Exception as exc:
        log.error("[loader] Error cargando PKL %s: %s", path.name, exc)
        return None


def load_model_pth(
    path: Union[str, Path],
    model_class: Optional[type] = None,
    **model_kwargs,
) -> Optional[nn.Module]:
    """
    Carga de forma segura un modelo PyTorch desde disco.

    Soporta dos casos:
      A) torch.save(model, path)         → modelo completo (devuelve directo)
      B) torch.save(model.state_dict())  → solo pesos (requiere model_class)

    Args:
        path        : Ruta al archivo .pth
        model_class : Clase del modelo (solo necesario para caso B).
        **model_kwargs : Argumentos para instanciar model_class (caso B).

    Returns:
        Modelo PyTorch en modo .eval(), o None si falla.
    """
    path = Path(path)
    if not path.exists():
        log.warning("[loader] Modelo PTH no encontrado: %s", path)
        return None

    try:
        datos = torch.load(path, map_location="cpu", weights_only=False)

        # Caso A: modelo completo
        if isinstance(datos, nn.Module):
            datos.eval()
            log.info("[loader] Modelo PTH cargado (completo): %s", path.name)
            return datos

        # Caso B: state_dict → necesitamos la clase
        if isinstance(datos, dict) and model_class is not None:
            modelo = model_class(**model_kwargs)
            modelo.load_state_dict(datos)
            modelo.eval()
            log.info("[loader] Modelo PTH cargado (state_dict) via %s", model_class.__name__)
            return modelo

        if isinstance(datos, dict) and model_class is None:
            log.warning(
                "[loader] El archivo contiene un state_dict pero no se pasó model_class. "
                "Devolviendo el dict raw."
            )

        return None

    except Exception as exc:
        log.error("[loader] Error cargando PTH %s: %s", path.name, exc)
        return None


# ── Test rápido ───────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

    BASE = Path(__file__).resolve().parent.parent.parent

    print("=" * 50)
    print("📦 HYDRO-V · Test loader.py")
    print("=" * 50)

    # Modelos
    pkl_path = BASE / "models" / "linear_autonomy.pkl"
    pth_path = BASE / "models" / "gnn_leak_detector_best.pth"

    model_pkl = load_model_pkl(pkl_path)
    print(f"PKL: {type(model_pkl).__name__}" if model_pkl else "PKL: no encontrado")

    model_pth = load_model_pth(pth_path)
    print(f"PTH: {type(model_pth).__name__}" if model_pth else "PTH: no encontrado")

    # CSVs (opcionales)
    telemetry_csv = BASE / "data" / "synthetic_leaks.csv"
    autonomy_csv  = BASE / "data" / "synthetic_autonomy.csv"

    if telemetry_csv.exists():
        df = load_telemetry_csv(telemetry_csv)
        print(f"Telemetría CSV: {df.shape}")
    else:
        print(f"CSV telemetría no existe aún — ejecutá generate_synthetic_data.py --save-data")

    if autonomy_csv.exists():
        X, y = load_autonomy_csv(autonomy_csv)
        print(f"Autonomía CSV: X={X.shape}  y={y.shape}")
    else:
        print(f"CSV autonomía no existe aún — ejecutá generate_synthetic_data.py --save-data")
