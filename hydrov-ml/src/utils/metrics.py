# ============================================================
#  Hydro-V · Métricas de Evaluación
#  Archivo: src/utils/metrics.py
# ============================================================

from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, roc_auc_score, mean_absolute_error,
    mean_squared_error, r2_score,
)


def evaluar_clasificador(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """
    Calcula métricas de clasificación binaria para la GNN.

    Args:
        y_true: Etiquetas reales.
        y_pred: Predicciones del modelo.

    Returns:
        Diccionario con accuracy, precision, recall, f1.
    """
    return {
        "accuracy":  round(accuracy_score(y_true, y_pred), 4),
        "precision": round(precision_score(y_true, y_pred, zero_division=0), 4),
        "recall":    round(recall_score(y_true, y_pred, zero_division=0), 4),
        "f1":        round(f1_score(y_true, y_pred, zero_division=0), 4),
    }


def evaluar_regresion(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """
    Calcula métricas de regresión para el modelo de autonomía.

    Args:
        y_true: Días de autonomía reales.
        y_pred: Días de autonomía predichos.

    Returns:
        Diccionario con MAE, RMSE y R².
    """
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)

    return {
        "mae":  round(mae, 4),
        "rmse": round(rmse, 4),
        "r2":   round(r2, 4),
    }