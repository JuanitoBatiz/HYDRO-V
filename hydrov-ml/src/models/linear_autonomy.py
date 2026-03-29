# ============================================================
#  Hydro-V · Predicción de Autonomía Hídrica (Modelo Híbrido)
#  Archivo: src/models/linear_autonomy.py
# ============================================================

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Optional

import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler


# ── Features ─────────────────────────────────────────────────
FEATURE_NAMES = [
    "nivel_actual_litros",
    "consumo_7d_lpm",
    "consumo_30d_lpm",
    "precipitacion_mm",
    "dia_semana",
    "mes",
]


# ── Coeficientes físicos (fallback sin entrenamiento) ────────
PHYSICAL_COEFFICIENTS = np.array([
    0.002,   # nivel_actual_litros
   -0.5,     # consumo_7d_lpm
   -0.3,     # consumo_30d_lpm
    0.05,    # precipitacion_mm
    0.01,    # dia_semana
    0.02,    # mes
])

PHYSICAL_INTERCEPT = 2.0


class AutonomyPredictor:
    """
    Modelo híbrido:
    - Entrenable con datos reales (ML)
    - Fallback físico si no hay modelo entrenado
    """

    def __init__(self) -> None:
        self.model = LinearRegression()
        self.scaler = StandardScaler()
        self._is_fitted = False

    # ── Entrenamiento ─────────────────────────────────────────
    def fit(self, X: np.ndarray, y: np.ndarray) -> "AutonomyPredictor":
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)
        self._is_fitted = True
        return self

    # ── Predicción ────────────────────────────────────────────
    def predict(self, X: np.ndarray) -> np.ndarray:
        if self._is_fitted:
            X_scaled = self.scaler.transform(X)
            preds = self.model.predict(X_scaled)
        else:
            # 🔥 Fallback físico
            preds = np.dot(X, PHYSICAL_COEFFICIENTS) + PHYSICAL_INTERCEPT

        return np.clip(preds, a_min=0, a_max=None)

    # ── Diagnóstico ───────────────────────────────────────────
    def get_coefficients(self) -> dict:
        if not self._is_fitted:
            return {
                "modo": "fisico",
                "intercepto": PHYSICAL_INTERCEPT,
                **{
                    name: coef
                    for name, coef in zip(FEATURE_NAMES, PHYSICAL_COEFFICIENTS)
                },
            }

        return {
            "modo": "entrenado",
            "intercepto": float(self.model.intercept_),
            **{
                name: float(coef)
                for name, coef in zip(FEATURE_NAMES, self.model.coef_)
            },
        }

    # ── Persistencia ──────────────────────────────────────────
    def save(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(
                {
                    "model": self.model,
                    "scaler": self.scaler,
                },
                f
            )
        print(f"[AutonomyPredictor] Modelo guardado en: {path}")

    @classmethod
    def load(cls, path: str) -> "AutonomyPredictor":
        instance = cls()

        if not Path(path).exists():
            print("⚠️ Modelo no encontrado. Usando modo físico (fallback).")
            return instance

        with open(path, "rb") as f:
            data = pickle.load(f)

        instance.model = data["model"]
        instance.scaler = data["scaler"]
        instance._is_fitted = True

        print(f"[AutonomyPredictor] Modelo cargado desde: {path}")
        return instance


# ── Test rápido ───────────────────────────────────────────────
if __name__ == "__main__":
    print("🤖 Test de AutonomyPredictor")

    predictor = AutonomyPredictor()

    X_test = np.array([[
        500.0,   # litros
        2.5,     # consumo 7d
        2.3,     # consumo 30d
        0.0,     # lluvia
        2,       # martes
        3        # marzo
    ]])

    pred = predictor.predict(X_test)
    print("Predicción (modo físico):", pred[0])

    print("\nCoeficientes:")
    print(predictor.get_coefficients())