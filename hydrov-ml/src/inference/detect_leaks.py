# ============================================================
#  Hydro-V · Inferencia — Detección de Fugas con GNN + Fallback
#  Archivo: src/inference/detect_leaks.py
# ============================================================

from __future__ import annotations

import torch
import numpy as np
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.models.gnn_leak_detection import HydroGNN
from src.data.synthetic_generator import construir_grafo_instantaneo

# Fallback opcional (modelo ligero)
try:
    from src.models.mlp_leak_detection import build_model as build_mlp
except ImportError:
    build_mlp = None


# ── Configuración ─────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent
MODEL_PATH = BASE_DIR / "models" / "gnn_leak_detector_best.pth"

UMBRAL_ANOMALIA = 0.75
IN_CHANNELS = 8


@dataclass
class AnomaliaDetectada:
    device_id: str
    probabilidad: float
    severidad: str
    detectado_en: str


class LeakDetector:
    """
    Detector híbrido:
    - Usa GNN para análisis completo de red
    - Puede usar MLP como fallback si el modelo no está disponible
    """

    def __init__(
        self,
        model_path: Path = MODEL_PATH,
        use_gnn: bool = True
    ) -> None:

        self.use_gnn = use_gnn
        self.model = None

        if use_gnn:
            try:
                self.model = HydroGNN(in_channels=IN_CHANNELS)
                self.model.load_state_dict(
                    torch.load(model_path, map_location="cpu")
                )
                print(f"[LeakDetector] GNN cargada desde: {model_path}")

            except FileNotFoundError:
                print("⚠️ Modelo GNN no encontrado. Usando fallback MLP...")
                self._load_mlp()

        else:
            self._load_mlp()

        self.model.eval()

    def _load_mlp(self):
        if build_mlp is None:
            raise RuntimeError("No hay modelo disponible (ni GNN ni MLP).")

        self.model = build_mlp()
        print("[LeakDetector] Usando modelo MLP (fallback)")

    def detectar(self, df_red) -> list[AnomaliaDetectada]:
        grafo = construir_grafo_instantaneo(df_red)

        with torch.no_grad():
            if self.use_gnn:
                logits = self.model(grafo.x, grafo.edge_index)
                probs = torch.exp(logits)
                prob_anomalia = probs[:, 1].numpy()

            else:
                # Fallback simple: inferencia nodo por nodo
                prob_anomalia = []
                for node_features in grafo.x:
                    score = float(self.model(node_features.unsqueeze(0)))
                    prob_anomalia.append(score)

                prob_anomalia = np.array(prob_anomalia)

        anomalias = []
        timestamp_iso = datetime.now(timezone.utc).isoformat() + "Z"

        for i, prob in enumerate(prob_anomalia):
            if prob >= UMBRAL_ANOMALIA:
                node_id = i + 2
                anomalias.append(
                    AnomaliaDetectada(
                        device_id=f"HYDRO-V-{node_id:03d}",
                        probabilidad=float(prob),
                        severidad="ALTA" if prob >= 0.90 else "MEDIA",
                        detectado_en=timestamp_iso,
                    )
                )

        return anomalias


# ── Test manual ───────────────────────────────────────────────
if __name__ == "__main__":
    from src.data.synthetic_generator import generar_red_completa

    print("==================================================")
    print("🌐 HYDRO-V: ESCÁNER DE RED (GNN + FALLBACK)")
    print("==================================================")

    try:
        detector = LeakDetector()

        print("📡 Simulando telemetría...")
        df_red_simulada = generar_red_completa(dias=1)

        print("🧠 Ejecutando inferencia...")
        alertas = detector.detectar(df_red_simulada)

        print("\n==================================================")
        print("🚨 REPORTE DE FUGAS")
        print("==================================================")

        if not alertas:
            print("✅ Sin anomalías detectadas.")
        else:
            print(f"⚠️ {len(alertas)} posibles fugas:")
            for alerta in alertas:
                print(f"📍 {alerta.device_id} | {alerta.probabilidad:.1%} | {alerta.severidad}")

    except Exception as e:
        print(f"🛑 Error en inferencia: {e}")