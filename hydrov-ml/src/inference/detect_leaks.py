# hydrov-ml/src/inference/detect_leaks.py
import torch
import numpy as np
from pathlib import Path
from typing import Optional

MODEL_PATH = Path(__file__).parent.parent.parent / "models" / "gnn_leak_detector_best.pth"

# Umbral de anomalía para clasificar como fuga
LEAK_THRESHOLD = 0.75


def load_model():
    model = torch.load(MODEL_PATH, map_location=torch.device("cpu"))
    model.eval()
    return model


# Modelo cargado una sola vez al importar
_model = load_model()


def detect_leak(
    node_id:      str,
    flow_lpm:     float,          # Flujo actual del nodo
    level_pct:    float,          # Nivel actual de cisterna
    neighbor_flows: list[float],  # Flujos de nodos vecinos (para GNN)
    neighbor_levels: list[float], # Niveles de nodos vecinos
) -> dict:
    """
    Detecta anomalías de flujo que podrían indicar fugas en la red.
    Usa la GNN para correlacionar con nodos vecinos.

    Retorna:
        {
            "node_id":        str,
            "leak_detected":  bool,
            "anomaly_score":  float,   # 0.0 a 1.0
            "confidence":     float,
        }
    """
    # Construir features del nodo central + vecinos
    node_features = [flow_lpm, level_pct]
    neighbor_features = []

    for f, l in zip(neighbor_flows, neighbor_levels):
        neighbor_features.extend([f, l])

    # Si no hay vecinos, inferencia solo con nodo local
    all_features = node_features + neighbor_features
    x = torch.tensor([all_features], dtype=torch.float32)

    with torch.no_grad():
        score = float(_model(x).squeeze())

    score = max(0.0, min(1.0, score))  # clamp entre 0 y 1

    return {
        "node_id":       node_id,
        "leak_detected": score >= LEAK_THRESHOLD,
        "anomaly_score": round(score, 4),
        "confidence":    0.80,   # placeholder hasta tener métricas reales
    }