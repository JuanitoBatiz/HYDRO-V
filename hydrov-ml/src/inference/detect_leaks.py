# ============================================================
#  Hydro-V · Inferencia — Detección de Fugas
#  Archivo: src/inference/detect_leaks.py
# ============================================================
#
#  Expone DOS interfaces públicas:
#
#  1. detect_leak(node_id, flow_lpm, level_pct, ...) -> dict
#     ── Función de alto nivel. Recibe los datos sueltos de un
#        nodo, construye el vector de features internamente y
#        retorna un dict listo para la API. Es la que llama
#        ml_service.py (backend FastAPI).
#
#  2. LeakDetector (clase)
#     ── Detector con análisis de red completo via GNN.
#        Úsala cuando tengas el DataFrame de todos los nodos.
#
#  Jerarquía de modelos (en orden de preferencia):
#    1. LeakDetectorMLP  (cargado desde .pth — rápido, 1 nodo)
#    2. Reglas físicas   (sin modelo — siempre disponible)
# ============================================================

from __future__ import annotations

import torch
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.models.gnn_leak_detection import HydroGNN, LeakDetectorMLP


# ── Configuración ─────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent.parent.parent
MODEL_PATH = BASE_DIR / "models" / "gnn_leak_detector_best.pth"

UMBRAL_ANOMALIA = 0.75   # score >= 0.75 → fuga detectada
UMBRAL_ALTA     = 0.90   # score >= 0.90 → severidad ALTA

# Rangos físicos para normalización
FLOW_MAX_LPM  = 30.0
LEVEL_MAX_PCT = 100.0


# ── Carga de modelo (singleton con lazy-load) ─────────────────
_modelo_cache: Optional[torch.nn.Module] = None


def _load_model() -> Optional[torch.nn.Module]:
    """
    Carga el modelo de detección de fugas desde disco.
    Soporta dos formatos guardados:
      - torch.save(model, path)         → modelo completo
      - torch.save(model.state_dict(), path) → solo pesos (HydroGNN)

    Retorna el modelo listo para inferencia, o None si falla.
    """
    global _modelo_cache
    if _modelo_cache is not None:
        return _modelo_cache

    if not MODEL_PATH.exists():
        print(f"[LeakDetector] ⚠️  Modelo no encontrado en {MODEL_PATH}. Usando reglas físicas.")
        return None

    try:
        datos = torch.load(MODEL_PATH, map_location="cpu", weights_only=False)

        # Caso A: Se guardó el modelo completo (torch.save(model, path))
        if isinstance(datos, torch.nn.Module):
            datos.eval()
            _modelo_cache = datos
            print(f"[LeakDetector] ✓ Modelo MLP cargado (completo) desde {MODEL_PATH}")
            return _modelo_cache

        # Caso B: Se guardó solo el state_dict (OrderedDict)
        if isinstance(datos, dict):
            modelo = LeakDetectorMLP(hidden_dim=32)
            try:
                modelo.load_state_dict(datos)
                modelo.eval()
                _modelo_cache = modelo
                print(f"[LeakDetector] ✓ Modelo MLP cargado (state_dict) desde {MODEL_PATH}")
                return _modelo_cache
            except RuntimeError:
                # El state_dict puede ser de HydroGNN — ignorar, usar físico
                print("[LeakDetector] ⚠️  state_dict incompatible con MLP. Usando reglas físicas.")
                return None

    except Exception as exc:
        print(f"[LeakDetector] ⚠️  Error al cargar modelo: {exc}. Usando reglas físicas.")
        return None


# ── Constructor de features ───────────────────────────────────

def _build_features(
    flow_lpm:        float,
    level_pct:       float,
    neighbor_flows:  list[float],
    neighbor_levels: list[float],
) -> np.ndarray:
    """
    Construye el vector de 10 features para el LeakDetectorMLP.

    Dimensiones (LeakDetectorMLP.MAX_INPUT_DIM = 10):
        [0] flow_lpm_norm          — flujo del nodo (0–1)
        [1] level_pct_norm         — nivel de cisterna (0–1)
        [2] avg_neighbor_flow_norm — flujo medio de vecinos (0–1)
        [3] avg_neighbor_level_norm— nivel medio de vecinos (0–1)
        [4] flow_deviation         — |flujo_nodo − flujo_vecinos| (0–1)
        [5] level_deviation        — |nivel_nodo − nivel_vecinos| (0–1)
        [6] is_low_level           — 1 si nivel < 20 % (señal de vaciado)
        [7] is_high_flow_low_level — 1 si flujo alto Y nivel bajo
        [8] pad_0                  — reservado
        [9] pad_1                  — reservado
    """
    # Valores de vecinos (con fallback al propio nodo si no hay vecinos)
    avg_n_flow  = float(np.mean(neighbor_flows))  if neighbor_flows  else flow_lpm
    avg_n_level = float(np.mean(neighbor_levels)) if neighbor_levels else level_pct

    flow_norm        = min(flow_lpm  / FLOW_MAX_LPM,  1.0)
    level_norm       = min(level_pct / LEVEL_MAX_PCT, 1.0)
    avg_n_flow_norm  = min(avg_n_flow  / FLOW_MAX_LPM,  1.0)
    avg_n_level_norm = min(avg_n_level / LEVEL_MAX_PCT, 1.0)

    flow_deviation  = abs(flow_norm  - avg_n_flow_norm)
    level_deviation = abs(level_norm - avg_n_level_norm)

    is_low_level           = 1.0 if level_pct < 20.0 else 0.0
    is_high_flow_low_level = 1.0 if (flow_lpm > 4.0 and level_pct < 40.0) else 0.0

    return np.array(
        [flow_norm, level_norm, avg_n_flow_norm, avg_n_level_norm,
         flow_deviation, level_deviation,
         is_low_level, is_high_flow_low_level,
         0.0, 0.0],   # padding
        dtype=np.float32,
    )


# ── Fallback físico ───────────────────────────────────────────

def _physics_score(
    flow_lpm:        float,
    level_pct:       float,
    avg_n_flow:      float,
    avg_n_level:     float,
) -> float:
    """
    Heurística física para detección de fugas cuando no hay modelo.

    Señales de fuga:
      1. Flujo alto + cisterna vaciándose rápido   → +0.50
      2. Flujo del nodo muy diferente a vecinos    → +0.25
      3. Nivel crítico (<10 %) + flujo positivo    → +0.20
      4. Nivel bajando mientras vecinos estables   → +0.15
    """
    score = 0.0

    if flow_lpm > 6.0 and level_pct < 30.0:
        score += 0.50

    flow_diff = abs(flow_lpm - avg_n_flow)
    if flow_diff > 4.0:
        score += 0.25
    elif flow_diff > 2.0:
        score += 0.10

    if level_pct < 10.0 and flow_lpm > 0.5:
        score += 0.20

    level_diff = level_pct - avg_n_level
    if level_diff < -15.0:          # el nodo pierde nivel más rápido que sus vecinos
        score += 0.15

    return round(min(score, 1.0), 4)


# ══════════════════════════════════════════════════════════════
#  FUNCIÓN PÚBLICA PRINCIPAL — usada por ml_service.py
# ══════════════════════════════════════════════════════════════

def detect_leak(
    node_id:         str,
    flow_lpm:        float,
    level_pct:       float,
    neighbor_flows:  list[float],
    neighbor_levels: list[float],
) -> dict:
    """
    Detecta si hay una fuga en el nodo indicado.

    Acepta los datos sueltos del nodo y construye internamente
    el vector de features — ml_service.py no necesita saber
    nada sobre la representación interna del modelo.

    Args:
        node_id         : Identificador del nodo, ej. "HYDRO-V-001".
        flow_lpm        : Flujo instantáneo del nodo (L/min).
        level_pct       : Nivel de cisterna del nodo (0–100 %).
        neighbor_flows  : Flujos de nodos vecinos hidráulicos.
        neighbor_levels : Niveles de nodos vecinos hidráulicos.

    Returns:
        dict con claves:
            node_id       (str)
            leak_detected (bool)
            anomaly_score (float)  — probabilidad de fuga [0.0–1.0]
            severity      (str)    — "NORMAL" | "MEDIA" | "ALTA"
            detected_at   (str)    — ISO 8601 UTC
    """
    features = _build_features(flow_lpm, level_pct, neighbor_flows, neighbor_levels)
    modelo   = _load_model()

    if modelo is not None:
        # ── Inferencia con modelo MLP ─────────────────────────
        x = torch.tensor(features).unsqueeze(0)   # [1, 10]
        with torch.no_grad():
            output = modelo(x)
            # Soportar salida con sigmoid (MLP) o log_softmax (GNN)
            if output.shape[-1] == 1:
                score = float(output.squeeze())
            else:
                # GNN: tomar prob de clase 1 (anomalía)
                score = float(torch.exp(output)[0, 1])
    else:
        # ── Fallback: reglas físicas ──────────────────────────
        avg_n_flow  = float(np.mean(neighbor_flows))  if neighbor_flows  else flow_lpm
        avg_n_level = float(np.mean(neighbor_levels)) if neighbor_levels else level_pct
        score = _physics_score(flow_lpm, level_pct, avg_n_flow, avg_n_level)

    leak_detected = score >= UMBRAL_ANOMALIA
    severity      = "ALTA" if score >= UMBRAL_ALTA else ("MEDIA" if leak_detected else "NORMAL")

    return {
        "node_id":       node_id,
        "leak_detected": leak_detected,
        "anomaly_score": round(score, 4),
        "severity":      severity,
        "detected_at":   datetime.now(timezone.utc).isoformat(),
    }


# ══════════════════════════════════════════════════════════════
#  CLASE LeakDetector — análisis de red completa (GNN)
#  Úsala cuando tengas el DataFrame de todos los nodos
# ══════════════════════════════════════════════════════════════

from dataclasses import dataclass


@dataclass
class AnomaliaDetectada:
    device_id:    str
    probabilidad: float
    severidad:    str
    detectado_en: str


class LeakDetector:
    """
    Detector a nivel de red completa usando HydroGNN.

    Recibe un DataFrame de la red (salida de generar_red_completa)
    y retorna la lista de nodos anómalos detectados.

    Para análisis nodo-a-nodo usá la función detect_leak() de arriba.
    """

    def __init__(self, model_path: Path = MODEL_PATH) -> None:
        self.model: Optional[torch.nn.Module] = None
        self._try_load_gnn(model_path)

    def _try_load_gnn(self, path: Path) -> None:
        """Intenta cargar HydroGNN; si falla usa MLP o fallback."""
        if not path.exists():
            print(f"[LeakDetector] ⚠️  Modelo no encontrado en {path}.")
            return

        try:
            datos = torch.load(path, map_location="cpu", weights_only=False)

            if isinstance(datos, HydroGNN):
                self.model = datos
                self.model.eval()
                print(f"[LeakDetector] ✓ HydroGNN cargada desde {path}")
                return

            if isinstance(datos, dict):
                gnn = HydroGNN(in_channels=8)
                gnn.load_state_dict(datos)
                gnn.eval()
                self.model = gnn
                print(f"[LeakDetector] ✓ HydroGNN (state_dict) cargada desde {path}")
                return

            # Es un MLP completo — también sirve para nodos individuales
            if isinstance(datos, torch.nn.Module):
                self.model = datos
                self.model.eval()
                print(f"[LeakDetector] ✓ Modelo MLP cargado como fallback desde {path}")
        except Exception as exc:
            print(f"[LeakDetector] ⚠️  Error al cargar: {exc}. Sin modelo de red.")

    def detectar(self, df_red) -> list[AnomaliaDetectada]:
        """
        Analiza toda la red y retorna nodos anómalos.

        Args:
            df_red: DataFrame de generar_red_completa()

        Returns:
            Lista de AnomaliaDetectada (puede estar vacía).
        """
        from src.data.synthetic_generator import construir_grafo_instantaneo

        grafo     = construir_grafo_instantaneo(df_red)
        timestamp = datetime.now(timezone.utc).isoformat() + "Z"
        anomalias = []

        if self.model is None:
            print("[LeakDetector] ⚠️  Sin modelo — retornando lista vacía.")
            return anomalias

        with torch.no_grad():
            output = self.model(grafo.x, grafo.edge_index) \
                if isinstance(self.model, HydroGNN) \
                else None   # MLP no recibe edge_index

        if output is None:
            return anomalias

        probs = torch.exp(output)[:, 1].numpy()   # prob de anomalía

        for i, prob in enumerate(probs):
            if prob >= UMBRAL_ANOMALIA:
                node_id = i + 2
                anomalias.append(
                    AnomaliaDetectada(
                        device_id=f"HYDRO-V-{node_id:03d}",
                        probabilidad=round(float(prob), 4),
                        severidad="ALTA" if prob >= UMBRAL_ALTA else "MEDIA",
                        detectado_en=timestamp,
                    )
                )

        return anomalias


# ── Test manual ───────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("🔍 HYDRO-V — Test detect_leak() (función pública)")
    print("=" * 55)

    casos = [
        ("HYDRO-V-001", 0.5,  85.0, [0.4, 0.6],  [82.0, 88.0], "Normal (cisterna llena, flujo bajo)"),
        ("HYDRO-V-002", 8.5,  12.0, [0.8, 1.2],  [80.0, 78.0], "Fuga probable (alto flujo, nivel bajo)"),
        ("HYDRO-V-003", 3.0,  55.0, [2.8, 3.2],  [53.0, 57.0], "Cosecha normal"),
        ("HYDRO-V-004", 10.0,  8.0, [1.0, 0.5],  [75.0, 72.0], "Fuga severa (nivel crítico)"),
    ]

    for node_id, flow, level, n_flows, n_levels, desc in casos:
        resultado = detect_leak(node_id, flow, level, n_flows, n_levels)
        estado    = "⚠️  FUGA" if resultado["leak_detected"] else "✓  Normal"
        print(
            f"\n{estado} | {desc}\n"
            f"         score={resultado['anomaly_score']:.4f} | "
            f"severidad={resultado['severity']} | "
            f"node={resultado['node_id']}"
        )