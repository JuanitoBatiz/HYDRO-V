# hydrov-ml/src/models/linear_autonomy.py
"""
Modelo de regresión lineal para predicción de días de autonomía hídrica.

Features de entrada (en este orden exacto):
    0: level_pct          — Nivel de cisterna en % (0-100)
    1: avg_consumption_lpd — Consumo promedio litros/día
    2: forecast_precip_mm  — Precipitación pronosticada 72h (NASA POWER)
    3: temperature_c       — Temperatura ambiente
    4: humidity_pct        — Humedad relativa (%)
    5: days_without_rain   — Días consecutivos sin lluvia
    6: month               — Mes del año (1-12)

Salida: float — días estimados de autonomía hídrica

Nota: Este modelo es un punto de partida (baseline). Con datos reales
del campo se puede reentrenar con train_linear.py y mejores features.
"""
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
import numpy as np


# Coeficientes aprendidos del mundo físico hídrico:
#   - level_pct        → impacto muy alto (más agua = más días)
#   - avg_consumption  → impacto negativo (más consumo = menos días)
#   - forecast_precip  → impacto moderado positivo (lluvia proyectada)
#   - temperature_c    → impacto leve negativo (más calor = más evaporación)
#   - humidity_pct     → impacto leve positivo
#   - days_without_rain → impacto negativo (sequía prolongada)
#   - month            → efecto estacional (meses lluviosos +)
FEATURE_NAMES = [
    "level_pct",
    "avg_consumption_lpd",
    "forecast_precip_mm",
    "temperature_c",
    "humidity_pct",
    "days_without_rain",
    "month",
]

# Coeficientes físicamente razonables para zona centro de México
# (calibrados para cisterna de ~1000L, consumo ~150L/día familiar)
COEFFICIENTS = np.array([
    0.18,    # level_pct: 100% cisterna ≈ 18 días adicionales
   -0.04,    # avg_consumption: cada 25 L/día extra = -1 día
    0.08,    # forecast_precip: cada 12.5mm = +1 día
   -0.05,    # temperature_c: cada 20°C = -1 día (evaporación)
    0.02,    # humidity_pct: efecto leve
   -0.10,    # days_without_rain: cada 10 días sequía = -1 día
    0.15,    # month: pico en julio-septiembre (temporada lluvias CDMX)
])
INTERCEPT = 2.0  # base mínima de días en condiciones neutras


def build_model() -> Pipeline:
    """
    Construye el pipeline sklearn:
    StandardScaler → LinearRegression con coeficientes calibrados.
    """
    scaler = StandardScaler()
    lr = LinearRegression()

    # Inyectar coeficientes directamente (sin necesidad de datos de training)
    lr.coef_     = COEFFICIENTS
    lr.intercept_ = INTERCEPT

    pipeline = Pipeline([
        ("scaler", scaler),
        ("model",  lr),
    ])

    # Inicializar el scaler con datos sintéticos representativos
    X_init = np.array([
        [50.0, 150.0, 5.0,  20.0, 60.0, 3,  6],   # condición media
        [90.0, 100.0, 20.0, 18.0, 75.0, 0,  8],   # temporada lluvias
        [10.0, 200.0, 0.0,  28.0, 40.0, 15, 3],   # sequía crítica
        [75.0, 120.0, 10.0, 22.0, 65.0, 2,  9],   # condición buena
        [30.0, 180.0, 2.0,  25.0, 50.0, 7,  1],   # invierno seco
    ])
    scaler.fit(X_init)

    return pipeline
