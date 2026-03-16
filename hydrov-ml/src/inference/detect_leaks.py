# ============================================================
#  Hydro-V · Inferencia — Detección de Fugas con GNN
#  Archivo: src/inference/detect_leaks.py
# ============================================================
#
#  Este script es llamado por el backend FastAPI cada 5 minutos
#  (cron job) para detectar anomalías en la red hídrica.
#
#  Cuando el hardware esté operativo, los datos vendrán de
#  InfluxDB en lugar del generador sintético.
#
# ============================================================

from __future__ import annotations

import torch
import numpy as np
from dataclasses import dataclass
from datetime import datetime

from src.models.gnn_leak_detection import HydroGNN
from src.data.synthetic_generator import construir_grafo_instantaneo


# ── Configuración ─────────────────────────────────────────────
UMBRAL_ANOMALIA = 0.75      # Probabilidad mínima para reportar anomalía
MODEL_PATH = "models/gnn_leak_detector_best.pth"
IN_CHANNELS = 8


@dataclass
class AnomaliaDetectada:
    """Resultado de una detección de anomalía en un nodo."""
    device_id: str
    probabilidad: float
    severidad: str          # "ALTA" o "MEDIA"
    detectado_en: str       # Timestamp ISO 8601


class LeakDetector:
    """
    Carga el modelo GNN entrenado y ejecuta inferencia
    sobre la red hídrica completa.

    Uso:
        detector = LeakDetector()
        anomalias = detector.detectar(df_red)
    """

    def __init__(self, model_path: str = MODEL_PATH) -> None:
        self.model = HydroGNN(in_channels=IN_CHANNELS)
        self.model.load_state_dict(
            torch.load(model_path, map_location="cpu")
        )
        self.model.eval()
        print(f"[LeakDetector] Modelo cargado desde: {model_path}")

    def detectar(self, df_red) -> list[AnomaliaDetectada]:
        """
        Detecta anomalías en la red hídrica.

        Args:
            df_red: DataFrame completo de la red (de synthetic_generator
                    o de InfluxDB cuando el hardware esté operativo).

        Returns:
            Lista de AnomaliaDetectada (vacía si no hay anomalías).
        """
        grafo = construir_grafo_instantaneo(df_red)

        with torch.no_grad():
            logits = self.model(grafo.x, grafo.edge_index)
            # log_softmax → softmax para obtener probabilidades reales
            probs = torch.exp(logits)
            prob_anomalia = probs[:, 1].numpy()   # Clase 1 = anomalía

        anomalias = []
        timestamp_iso = datetime.utcnow().isoformat() + "Z"

        for i, prob in enumerate(prob_anomalia):
            if prob >= UMBRAL_ANOMALIA:
                node_id = i + 2   # Nodos 2–50 (el 1 es el real)
                anomalias.append(
                    AnomaliaDetectada(
                        device_id=f"HYDRO-V-{node_id:03d}",
                        probabilidad=float(prob),
                        severidad="ALTA" if prob >= 0.90 else "MEDIA",
                        detectado_en=timestamp_iso,
                    )
                )

        return anomalias