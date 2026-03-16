# ============================================================
#  Hydro-V · Predicción de Autonomía Hídrica
#  Archivo: src/models/linear_autonomy.py
#  Algoritmo: Regresión Lineal Múltiple (scikit-learn OLS)
# ============================================================
#
#  Predice cuántos días de agua le quedan al usuario basándose
#  en el nivel actual de la cisterna, el consumo histórico y
#  el pronóstico de lluvia de la NASA POWER API.
#
#  Ecuación del modelo:
#    días = β₀
#           + β₁·nivel_actual_litros
#           + β₂·consumo_7d_lpm
#           + β₃·consumo_30d_lpm
#           + β₄·precipitacion_mm
#           + β₅·dia_semana
#           + β₆·mes
#
# ============================================================

import pickle
from pathlib import Path
from typing import Optional

import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler


# Features en el mismo orden que se usan para entrenar y predecir
FEATURE_NAMES = [
    "nivel_actual_litros",
    "consumo_7d_lpm",
    "consumo_30d_lpm",
    "precipitacion_mm",
    "dia_semana",   # 0 (lunes) – 6 (domingo)
    "mes",          # 1 – 12
]


class AutonomyPredictor:
    """
    Wrapper para el modelo de regresión lineal de autonomía hídrica.

    Uso típico:
        predictor = AutonomyPredictor()
        predictor.fit(X_train, y_train)
        predictor.save("models/linear_autonomy.pkl")

        # En producción:
        predictor = AutonomyPredictor.load("models/linear_autonomy.pkl")
        dias = predictor.predict(X_nuevo)
    """

    def __init__(self) -> None:
        self.model = LinearRegression()
        self.scaler = StandardScaler()
        self.feature_names = FEATURE_NAMES
        self._is_fitted = False

    # ------------------------------------------------------------------
    # Entrenamiento
    # ------------------------------------------------------------------

    def fit(self, X: np.ndarray, y: np.ndarray) -> "AutonomyPredictor":
        """
        Entrena el modelo.

        Args:
            X: Matriz de features [n_muestras, 6].
            y: Vector de días de autonomía reales [n_muestras].

        Returns:
            self (para encadenamiento de métodos).
        """
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)
        self._is_fitted = True
        return self

    # ------------------------------------------------------------------
    # Predicción
    # ------------------------------------------------------------------

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Predice días de autonomía restantes.

        Args:
            X: Matriz de features [n_muestras, 6].

        Returns:
            Array de predicciones [n_muestras].
        """
        if not self._is_fitted:
            raise RuntimeError("El modelo no ha sido entrenado. Llama a .fit() primero.")

        X_scaled = self.scaler.transform(X)
        predictions = self.model.predict(X_scaled)

        # Los días no pueden ser negativos
        return np.clip(predictions, a_min=0, a_max=None)

    # ------------------------------------------------------------------
    # Diagnóstico
    # ------------------------------------------------------------------

    def get_coefficients(self) -> dict:
        """Retorna los coeficientes del modelo con nombre de feature."""
        if not self._is_fitted:
            raise RuntimeError("El modelo no ha sido entrenado.")

        return {
            "intercepto": float(self.model.intercept_),
            **{
                name: float(coef)
                for name, coef in zip(self.feature_names, self.model.coef_)
            },
        }

    # ------------------------------------------------------------------
    # Persistencia
    # ------------------------------------------------------------------

    def save(self, path: str) -> None:
        """Guarda el modelo entrenado en disco (formato pickle)."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({"model": self.model, "scaler": self.scaler}, f)
        print(f"[AutonomyPredictor] Modelo guardado en: {path}")

    @classmethod
    def load(cls, path: str) -> "AutonomyPredictor":
        """Carga un modelo previamente entrenado desde disco."""
        with open(path, "rb") as f:
            data = pickle.load(f)

        instance = cls()
        instance.model = data["model"]
        instance.scaler = data["scaler"]
        instance._is_fitted = True
        print(f"[AutonomyPredictor] Modelo cargado desde: {path}")
        return instance
if __name__ == "__main__":
    import pandas as pd
    import os

    print("🏋️‍♂️ Entrenando el modelo de Regresión Lineal...")
    
    # Creamos un historial falso con las 6 variables exactas que espera el modelo
    df_entrenamiento = pd.DataFrame({
        'nivel_actual_litros': [1000.0, 500.0, 250.0, 800.0, 100.0],
        'consumo_7d_lpm': [2.0, 2.5, 3.0, 1.5, 4.0],
        'consumo_30d_lpm': [2.1, 2.4, 2.9, 1.6, 3.8],
        'precipitacion_mm': [0.0, 5.0, 0.0, 12.0, 0.0],
        'dia_semana': [0, 1, 2, 3, 4], # Lunes a Viernes
        'mes': [3, 3, 4, 4, 5],        # Marzo, Abril, Mayo
        'dias_restantes': [500, 200, 83, 533, 25] 
    })
    
    X = df_entrenamiento[['nivel_actual_litros', 'consumo_7d_lpm', 'consumo_30d_lpm', 'precipitacion_mm', 'dia_semana', 'mes']].values
    y = df_entrenamiento['dias_restantes'].values
    
    modelo = AutonomyPredictor()
    modelo.fit(X, y)
    
    os.makedirs('models', exist_ok=True)
    modelo.save('models/linear_autonomy.pkl')
    
    print("✅ ¡Modelo entrenado y guardado con éxito! El archivo ya tiene datos.")    