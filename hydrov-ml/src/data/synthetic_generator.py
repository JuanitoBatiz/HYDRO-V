# ============================================================
#  Hydro-V · Generador de Datos Sintéticos
#  Archivo: src/data/synthetic_generator.py
# ============================================================
#
#  Genera datos de sensores realistas para los 49 nodos
#  virtuales de la red hídrica de Neza.
#
#  Los datos simulan exactamente la telemetría que publica
#  el ESP32 HYDRO-V-001 vía MQTT:
#    - turbidity_ntu  (Sensor de turbidez analógico)
#    - flow_lpm       (Sensor de flujo YF-S201)
#    - distance_cm    (Sensor ultrasónico JSN-SR04T)
#    - flow_total     (Acumulado de litros)
#
#  Además añade las features de tiempo necesarias para la GNN:
#    - hora_sin / hora_cos   (Codificación cíclica de la hora)
#    - dia_sin  / dia_cos    (Codificación cíclica del día)
#
#  COLUMNAS DEL DATAFRAME GENERADO (8 features):
#    turbidez_norm, flujo_norm, nivel_norm, presion_est,
#    delta_turbidez, delta_flujo, hora_sin, hora_cos
#
# ============================================================

from __future__ import annotations

import numpy as np
import pandas as pd
import torch
from torch_geometric.data import Data


# ── Constantes del sistema físico ────────────────────────────
CISTERNA_LITROS = 1_100      # Capacidad máxima de la cisterna (litros)
FLUJO_MAX_LPM = 30.0         # Caudal máximo del sensor YF-S201
TURBIDEZ_MAX_NTU = 1_000.0   # Rango máximo del sensor de turbidez
DISTANCIA_MAX_CM = 500.0     # Rango máximo del sensor ultrasónico


# ── Perfiles de colonia (variaciones por zona geográfica) ────
# Cada colonia tiene un multiplicador de consumo diferente
# basado en datos típicos de Nezahualcóyotl.
PERFILES_COLONIA = {
    "El Sol":           {"consumo": 1.2, "turbidez_base": 45.0},
    "Juárez Pantitlán": {"consumo": 0.8, "turbidez_base": 60.0},
    "Benito Juárez":    {"consumo": 1.0, "turbidez_base": 50.0},
    "Ciudad Lago":      {"consumo": 1.1, "turbidez_base": 55.0},
    "Las Flores":       {"consumo": 0.9, "turbidez_base": 40.0},
}

# Colonias asignadas a los 49 nodos sintéticos
_COLONIAS_LISTA = list(PERFILES_COLONIA.keys())


def _colonia_para_nodo(node_id: int) -> str:
    """Asigna una colonia de forma determinista según el ID del nodo."""
    return _COLONIAS_LISTA[(node_id - 2) % len(_COLONIAS_LISTA)]


# ── Generador principal ───────────────────────────────────────

def generar_datos_nodo(
    node_id: int,
    dias: int = 60,
    seed: int | None = None,
) -> pd.DataFrame:
    """
    Genera un DataFrame con lecturas de sensores sintéticas para
    un nodo de la red hídrica.

    Las lecturas se producen cada 5 minutos (igual que el ESP32),
    resultando en 288 muestras por día.

    Args:
        node_id (int): ID del nodo (2–50). El nodo 1 es el real.
        dias    (int): Número de días a simular. Por defecto 60.
        seed    (int): Semilla aleatoria para reproducibilidad.

    Returns:
        pd.DataFrame con columnas:
            device_id, timestamp, turbidity_ntu, flow_lpm,
            distance_cm, flow_total, hora_sin, hora_cos,
            dia_sin, dia_cos, label
    """
    rng = np.random.default_rng(seed if seed is not None else node_id * 42)

    colonia = _colonia_para_nodo(node_id)
    perfil = PERFILES_COLONIA[colonia]
    device_id = f"HYDRO-V-{node_id:03d}"

    # ── Timestamps: cada 5 minutos durante 'dias' días ──────────
    n_muestras = dias * 24 * 12   # 12 muestras por hora × 24 horas
    timestamps = pd.date_range(
        start="2025-01-01",
        periods=n_muestras,
        freq="5min",
    )

    horas = timestamps.hour + timestamps.minute / 60.0
    dias_semana = timestamps.dayofweek   # 0=lunes … 6=domingo

    # ── Patrón de consumo diario (pico mañana y noche) ──────────
    # Simula el uso típico de una familia en Neza
    patron_hora = (
        0.3 * np.sin(2 * np.pi * (horas - 7) / 24)    # pico 7am
        + 0.4 * np.sin(2 * np.pi * (horas - 20) / 24)  # pico 8pm
        + 0.5
    )
    patron_hora = np.clip(patron_hora, 0, 1)

    # ── Flujo (LPM) ─────────────────────────────────────────────
    flujo_base = FLUJO_MAX_LPM * 0.15 * perfil["consumo"]
    flow_lpm = (
        flujo_base * patron_hora
        + rng.normal(0, 0.5, n_muestras)
    )
    flow_lpm = np.clip(flow_lpm, 0, FLUJO_MAX_LPM)

    # ── Nivel de cisterna (distancia ultrasónico en cm) ─────────
    # Simula ciclos de llenado/vaciado de 3-7 días
    ciclo_nivel = np.sin(
        2 * np.pi * np.arange(n_muestras) / (n_muestras / (dias / 5))
    )
    distance_cm = 150 + 80 * ciclo_nivel + rng.normal(0, 5, n_muestras)
    distance_cm = np.clip(distance_cm, 10, DISTANCIA_MAX_CM)

    # ── Turbidez (NTU) ──────────────────────────────────────────
    # Sube durante eventos de lluvia (días 10-12, 30-33 del periodo)
    turbidez_base = perfil["turbidez_base"]
    turbidity_ntu = rng.normal(turbidez_base, 15, n_muestras)

    # Inyectar picos de lluvia solo si el periodo es suficientemente largo.
    # Cada pico ocupa 2 y 3 días respectivamente, por eso necesitamos
    # al menos 12 días para el primero y 33 para el segundo.
    if dias >= 12:
        ini1, fin1 = 10 * 288, 12 * 288
        turbidity_ntu[ini1:fin1] += rng.uniform(100, 300, fin1 - ini1)

    if dias >= 33:
        ini2, fin2 = 30 * 288, 33 * 288
        turbidity_ntu[ini2:fin2] += rng.uniform(80, 250, fin2 - ini2)
    turbidity_ntu = np.clip(turbidity_ntu, 0, TURBIDEZ_MAX_NTU)

    # ── Flujo total acumulado ────────────────────────────────────
    flow_total = np.cumsum(flow_lpm * (5 / 60))   # LPM × minutos → litros

    # ── Etiquetas de anomalía (ground truth) ────────────────────
    # Una anomalía ocurre cuando la turbidez supera 200 NTU
    # (criterio derivado del umbral FSM del ESP32 > 500 ADC ≈ 122 NTU)
    label = (turbidity_ntu > 200).astype(int)

    # ── Codificación cíclica del tiempo ─────────────────────────
    hora_sin = np.sin(2 * np.pi * horas / 24)
    hora_cos = np.cos(2 * np.pi * horas / 24)
    dia_sin = np.sin(2 * np.pi * dias_semana / 7)
    dia_cos = np.cos(2 * np.pi * dias_semana / 7)

    return pd.DataFrame({
        "device_id":    device_id,
        "timestamp":    timestamps,
        "turbidity_ntu": turbidity_ntu,
        "flow_lpm":      flow_lpm,
        "distance_cm":   distance_cm,
        "flow_total":    flow_total,
        "hora_sin":      hora_sin,
        "hora_cos":      hora_cos,
        "dia_sin":       dia_sin,
        "dia_cos":       dia_cos,
        "label":         label,
    })


def generar_red_completa(dias: int = 60) -> pd.DataFrame:
    """
    Genera datos para los 49 nodos sintéticos (nodos 2–50).

    El nodo 1 (HYDRO-V-001) es el nodo real del ESP32; sus datos
    vendrán de InfluxDB cuando el hardware esté operativo.

    Args:
        dias (int): Días a simular por nodo. Por defecto 60.

    Returns:
        pd.DataFrame con todos los nodos concatenados.
    """
    print(f"[SyntheticGenerator] Generando datos para 49 nodos ({dias} días c/u)...")
    frames = []

    for node_id in range(2, 51):
        df = generar_datos_nodo(node_id, dias=dias, seed=node_id * 7)
        frames.append(df)
        if node_id % 10 == 0:
            print(f"  → Nodo {node_id}/50 completado")

    resultado = pd.concat(frames, ignore_index=True)
    total = len(resultado)
    anomalias = resultado["label"].sum()
    print(f"[SyntheticGenerator] Total muestras : {total:,}")
    print(f"[SyntheticGenerator] Anomalías       : {anomalias:,} ({anomalias/total*100:.1f}%)")
    return resultado


# ── Construcción del grafo PyTorch Geometric ─────────────────

def construir_grafo_instantaneo(
    df_red: pd.DataFrame,
    timestamp: pd.Timestamp | None = None,
) -> Data:
    """
    Construye un grafo PyTorch Geometric a partir de una instantánea
    de la red (todos los nodos en un mismo timestamp).

    Esto es lo que consume el modelo HydroGNN en tiempo de inferencia.

    Args:
        df_red    : DataFrame completo de la red (salida de generar_red_completa).
        timestamp : Momento del que extraer la instantánea.
                    Si es None, usa el último timestamp disponible.

    Returns:
        torch_geometric.data.Data con:
            x          : features [50, 8] (o 49 si no hay nodo real)
            edge_index : conectividad de la red [2, num_aristas]
            y          : etiquetas [50]
    """
    if timestamp is None:
        timestamp = df_red["timestamp"].max()

    # Filtrar la instantánea
    snap = df_red[df_red["timestamp"] == timestamp].copy()

    if snap.empty:
        # Tomar la muestra más cercana
        idx = (df_red["timestamp"] - timestamp).abs().idxmin()
        t_cercano = df_red.loc[idx, "timestamp"]
        snap = df_red[df_red["timestamp"] == t_cercano].copy()

    # Construir matriz de features [n_nodos, 8]
    feature_cols = [
        "turbidity_ntu", "flow_lpm", "distance_cm", "flow_total",
        "hora_sin", "hora_cos", "dia_sin", "dia_cos",
    ]

    # Normalizar a [0, 1]
    snap_feat = snap[feature_cols].copy()
    snap_feat["turbidity_ntu"] = snap_feat["turbidity_ntu"] / TURBIDEZ_MAX_NTU
    snap_feat["flow_lpm"] = snap_feat["flow_lpm"] / FLUJO_MAX_LPM
    snap_feat["distance_cm"] = snap_feat["distance_cm"] / DISTANCIA_MAX_CM
    snap_feat["flow_total"] = snap_feat["flow_total"] / max(float(snap_feat["flow_total"].max()), 1.0)

    x = torch.tensor(snap_feat.values, dtype=torch.float)
    y = torch.tensor(snap["label"].values, dtype=torch.long)

    # Construir aristas: conectar nodos vecinos (topología en anillo + saltos)
    n = len(snap)
    src, dst = [], []
    for i in range(n):
        for offset in [1, 2, 5]:   # vecino inmediato, siguiente, y salto
            j = (i + offset) % n
            src.extend([i, j])
            dst.extend([j, i])

    edge_index = torch.tensor([src, dst], dtype=torch.long)

    return Data(x=x, edge_index=edge_index, y=y)


# ── Bloque de validación ──────────────────────────────────────
if __name__ == "__main__":
    # 1. Generar un nodo individual
    print("=== Generando nodo individual ===")
    df_nodo = generar_datos_nodo(node_id=2, dias=5)
    print(df_nodo.head())
    print(f"Shape: {df_nodo.shape}")

    # 2. Generar la red completa (49 nodos, 60 días)
    print("\n=== Generando red completa ===")
    df_red = generar_red_completa(dias=60)
    print(df_red.groupby("device_id")["label"].mean().describe())

    # 3. Construir grafo para la GNN
    print("\n=== Construyendo grafo para GNN ===")
    grafo = construir_grafo_instantaneo(df_red)
    print(f"Nodos        : {grafo.num_nodes}")
    print(f"Aristas      : {grafo.num_edges}")
    print(f"Features/nodo: {grafo.num_node_features}")
    print(f"Etiquetas    : {grafo.y.shape}  → {grafo.y.sum().item()} anomalías")

    # 4. Verificar compatibilidad con HydroGNN
    from src.models.gnn_leak_detection import HydroGNN
    modelo = HydroGNN(in_channels=grafo.num_node_features)
    modelo.eval()
    with torch.no_grad():
        salida = modelo(grafo.x, grafo.edge_index)
    print(f"\nForward pass : {list(salida.shape)}  ✓ (esperado [{grafo.num_nodes}, 2])")