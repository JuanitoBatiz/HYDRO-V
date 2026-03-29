#!/usr/bin/env python3
# hydrov-backend/scripts/generate_synthetic_data.py
"""
Generador de modelos ML dummy para Hydro-V.

Propósito: crear los archivos .pkl y .pth que el backend necesita
para arrancar sin datos reales del campo. Los modelos generados son
funcionales — producen predicciones razonables sobre datos físicos
de captación pluvial en la zona centro de México.

Uso:
    cd HYDRO-V/
    python hydrov-backend/scripts/generate_synthetic_data.py

    # O solo un modelo específico:
    python hydrov-backend/scripts/generate_synthetic_data.py --model autonomy
    python hydrov-backend/scripts/generate_synthetic_data.py --model leaks
    python hydrov-backend/scripts/generate_synthetic_data.py --model all

Salida:
    hydrov-ml/models/linear_autonomy.pkl
    hydrov-ml/models/gnn_leak_detector_best.pth
    hydrov-ml/data/synthetic_autonomy.csv    (opcional, --save-data)
    hydrov-ml/data/synthetic_leaks.csv       (opcional, --save-data)
"""
import sys
import argparse
import pickle
import logging
from pathlib import Path

import numpy as np

# ── Setup de paths ────────────────────────────────────────────────
ROOT_DIR   = Path(__file__).resolve().parent.parent.parent  # HYDRO-V/
ML_SRC     = ROOT_DIR / "hydrov-ml" / "src"
MODELS_DIR = ROOT_DIR / "hydrov-ml" / "models"
DATA_DIR   = ROOT_DIR / "hydrov-ml" / "data"

sys.path.insert(0, str(ML_SRC))

# ── Logging ───────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("hydrov-ml-gen")


# ─────────────────────────────────────────────────────────────────
#  1. Generador de datos sintéticos para autonomía
# ─────────────────────────────────────────────────────────────────

def generate_autonomy_data(n_samples: int = 2000, seed: int = 42) -> tuple:
    """
    Genera datos sintéticos para entrenar el modelo de autonomía.

    Features (X):
        level_pct, avg_consumption_lpd, forecast_precip_mm,
        temperature_c, humidity_pct, days_without_rain, month

    Target (y):
        days_autonomy — calculado con física real de captación pluvial
    """
    rng = np.random.default_rng(seed)

    n = n_samples

    # ── Variables con distribuciones físicamente realistas ────────
    level_pct           = rng.uniform(5.0,  100.0,  n)    # % cisterna
    avg_consumption_lpd = rng.normal(150.0, 40.0,   n).clip(60, 300)  # L/día
    forecast_precip_mm  = rng.exponential(8.0,      n).clip(0, 80)    # mm en 72h
    temperature_c       = rng.normal(20.0,  4.0,    n).clip(10, 35)   # °C Neza
    humidity_pct        = rng.uniform(35.0, 85.0,   n)    # %
    days_without_rain   = rng.integers(0, 30,        n)   # días
    month               = rng.integers(1, 13,        n)   # 1-12

    # ── Cálculo físico de días de autonomía ───────────────────────
    # Modelo hidrológico simplificado:
    #   cisterna ≈ 1000L para área de techo 45m²
    #   volumen_disponible = level_pct * 10  (litros)
    #   aporte_lluvia = forecast_precip_mm * roof_area_m2 * 0.85  (eficiencia)
    #   dias = (volumen + aporte) / consumo_diario

    CISTERN_CAPACITY = 1000.0   # litros
    ROOF_AREA        = 45.0     # m²
    COLLECTION_EFF   = 0.85     # eficiencia de captación

    volumen_actual = level_pct / 100.0 * CISTERN_CAPACITY
    aporte_lluvia  = forecast_precip_mm * ROOF_AREA * COLLECTION_EFF / 1000.0 * 1000.0  # → litros
    volumen_total  = volumen_actual + aporte_lluvia

    days_autonomy = volumen_total / avg_consumption_lpd

    # Ajustes estacionales (temporada lluvias CDMX: mayo-octubre)
    season_factor = np.where(
        (month >= 5) & (month <= 10),
        1.0 + forecast_precip_mm * 0.01,   # bonus en temporada de lluvias
        1.0 - days_without_rain * 0.02,    # penalización en sequía
    )
    days_autonomy = (days_autonomy * season_factor).clip(0.0, 60.0)

    # Ruido realista
    noise = rng.normal(0.0, 0.3, n)
    days_autonomy = (days_autonomy + noise).clip(0.0)

    X = np.column_stack([
        level_pct, avg_consumption_lpd, forecast_precip_mm,
        temperature_c, humidity_pct, days_without_rain, month,
    ])
    y = days_autonomy

    return X, y


def train_autonomy_model(save_data: bool = False) -> None:
    """Entrena y serializa el modelo de autonomía hídrica."""
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import cross_val_score

    log.info("Generando datos sintéticos de autonomía hídrica...")
    X, y = generate_autonomy_data(n_samples=3000)

    log.info(f"  Muestras: {len(X)} | days_autonomy — min={y.min():.1f} max={y.max():.1f} mean={y.mean():.1f}")

    # Pipeline: estandarización + Ridge (más robusto que LinearRegression)
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("model",  Ridge(alpha=1.0)),
    ])

    # Cross-validation para verificar que el modelo aprende algo razonable
    scores = cross_val_score(pipeline, X, y, cv=5, scoring="r2")
    log.info(f"  R² cross-val: {scores.mean():.3f} ± {scores.std():.3f}")

    pipeline.fit(X, y)

    # ── Guardar modelo ────────────────────────────────────────────
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODELS_DIR / "linear_autonomy.pkl"

    with open(model_path, "wb") as f:
        pickle.dump(pipeline, f)

    log.info(f"  ✓ Modelo guardado en {model_path}")

    # ── Guardar datos sintéticos (opcional) ───────────────────────
    if save_data:
        import csv
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        csv_path = DATA_DIR / "synthetic_autonomy.csv"
        headers = [
            "level_pct", "avg_consumption_lpd", "forecast_precip_mm",
            "temperature_c", "humidity_pct", "days_without_rain", "month",
            "days_autonomy",
        ]
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for xi, yi in zip(X, y):
                writer.writerow(list(xi) + [round(yi, 2)])
        log.info(f"  ✓ Datos guardados en {csv_path}")

    # ── Verificación rápida ───────────────────────────────────────
    test_cases = [
        ([50.0, 150.0, 5.0,  20.0, 60.0, 3,  6], "media"),
        ([90.0, 100.0, 20.0, 18.0, 75.0, 0,  8], "buena (lluvias)"),
        ([10.0, 200.0, 0.0,  28.0, 40.0, 15, 3], "crítica (sequía)"),
    ]
    log.info("  Verificando predicciones:")
    for features, desc in test_cases:
        pred = pipeline.predict([features])[0]
        log.info(f"    {desc:20s} → {max(0, pred):.1f} días")


# ─────────────────────────────────────────────────────────────────
#  2. Generador del modelo de detección de fugas
# ─────────────────────────────────────────────────────────────────

def generate_leaks_data(n_samples: int = 2000, seed: int = 99) -> tuple:
    """
    Genera datos sintéticos para el detector de fugas.

    Features (X): [flow_lpm, level_pct]
    Target (y): 1.0 = fuga, 0.0 = normal

    Lógica física:
    - Fuga: flujo alto y nivel bajando rápidamente
    - Normal: flujo proporcional al nivel o cero (sin cosecha)
    """
    rng = np.random.default_rng(seed)
    n = n_samples

    X_list, y_list = [], []

    # ── Nodos normales (70% de los datos) ────────────────────────
    n_normal = int(n * 0.7)
    flow_normal  = rng.exponential(1.5, n_normal).clip(0, 8)    # L/min
    level_normal = rng.uniform(20.0, 95.0, n_normal)             # %
    X_list.append(np.column_stack([flow_normal, level_normal]))
    y_list.append(np.zeros(n_normal))

    # ── Nodos en estado HARVESTING normal (15%) ───────────────────
    n_harvest = int(n * 0.15)
    flow_harvest  = rng.uniform(2.0, 6.0,   n_harvest)
    level_harvest = rng.uniform(30.0, 80.0, n_harvest)
    X_list.append(np.column_stack([flow_harvest, level_harvest]))
    y_list.append(np.zeros(n_harvest))  # cosecha normal = no fuga

    # ── Nodos con fuga (15%) ──────────────────────────────────────
    n_leak = n - n_normal - n_harvest
    # Fuga: flujo inesperadamente alto para el nivel de cisterna
    flow_leak  = rng.uniform(4.0, 12.0,  n_leak)   # flujo alto
    level_leak = rng.uniform(5.0,  40.0, n_leak)   # nivel bajo (se vacía)
    X_list.append(np.column_stack([flow_leak, level_leak]))
    y_list.append(np.ones(n_leak))

    X = np.vstack(X_list)
    y = np.concatenate(y_list)

    # Shuffle
    idx = rng.permutation(len(X))
    return X[idx], y[idx]


def train_leaks_model(save_data: bool = False) -> None:
    """Entrena y serializa el modelo de detección de fugas como PyTorch."""
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset

    # Importar definición del modelo
    from models.gnn_leak_detection import LeakDetectorMLP

    log.info("Generando datos sintéticos de fugas...")
    X, y = generate_leaks_data(n_samples=3000)

    # Balance de clases
    n_leak   = int(y.sum())
    n_normal = len(y) - n_leak
    log.info(f"  Muestras: {len(X)} | Normal: {n_normal} | Fuga: {n_leak}")

    # ── Tensores ──────────────────────────────────────────────────
    # El modelo espera MAX_INPUT_DIM=10 — padding con ceros para 2 features
    X_padded = np.zeros((len(X), LeakDetectorMLP.MAX_INPUT_DIM))
    X_padded[:, :2] = X  # flow_lpm, level_pct en las primeras 2 cols

    X_tensor = torch.tensor(X_padded, dtype=torch.float32)
    y_tensor = torch.tensor(y, dtype=torch.float32).unsqueeze(1)

    dataset    = TensorDataset(X_tensor, y_tensor)
    dataloader = DataLoader(dataset, batch_size=64, shuffle=True)

    # ── Modelo ────────────────────────────────────────────────────
    model = LeakDetectorMLP(hidden_dim=32)

    # Peso de clase para manejar desbalance (fugas son minoría)
    pos_weight = torch.tensor([n_normal / n_leak], dtype=torch.float32)
    criterion  = nn.BCEWithLogitsLoss(pos_weight=pos_weight)

    # Usar Sigmoid en forward — reemplazar BCEWithLogitsLoss por BCE
    criterion  = nn.BCELoss()
    optimizer  = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-4)

    # ── Entrenamiento ─────────────────────────────────────────────
    model.train()
    EPOCHS = 30
    for epoch in range(EPOCHS):
        total_loss = 0.0
        for X_batch, y_batch in dataloader:
            optimizer.zero_grad()
            pred = model(X_batch)
            loss = criterion(pred, y_batch)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()

        if (epoch + 1) % 10 == 0:
            avg_loss = total_loss / len(dataloader)
            log.info(f"  Epoch {epoch+1:3d}/{EPOCHS} | Loss: {avg_loss:.4f}")

    model.eval()

    # ── Métricas rápidas ──────────────────────────────────────────
    with torch.no_grad():
        preds  = model(X_tensor).squeeze().numpy()
        binary = (preds >= 0.75).astype(int)
        acc    = (binary == y).mean()
        log.info(f"  Accuracy (threshold=0.75): {acc:.3f}")

    # ── Guardar modelo ────────────────────────────────────────────
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODELS_DIR / "gnn_leak_detector_best.pth"

    torch.save(model, model_path)
    log.info(f"  ✓ Modelo guardado en {model_path}")

    # ── Guardar datos (opcional) ──────────────────────────────────
    if save_data:
        import csv
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        csv_path = DATA_DIR / "synthetic_leaks.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["flow_lpm", "level_pct", "leak"])
            for xi, yi in zip(X, y):
                writer.writerow([round(xi[0], 3), round(xi[1], 2), int(yi)])
        log.info(f"  ✓ Datos guardados en {csv_path}")

    # ── Verificación rápida ───────────────────────────────────────
    test_cases = [
        ([0.5,  75.0], "normal (bajo flujo, cisterna llena)"),
        ([8.0,  15.0], "fuga probable (alto flujo, cisterna vacía)"),
        ([3.0,  60.0], "cosecha normal"),
    ]
    log.info("  Verificando predicciones:")
    for features, desc in test_cases:
        padded = features + [0.0] * (LeakDetectorMLP.MAX_INPUT_DIM - len(features))
        x = torch.tensor([padded], dtype=torch.float32)
        with torch.no_grad():
            score = float(model(x).squeeze())
        label = "⚠️ FUGA" if score >= 0.75 else "✓ Normal"
        log.info(f"    {desc:42s} → score={score:.3f} {label}")


# ─────────────────────────────────────────────────────────────────
#  CLI
# ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Genera modelos ML dummy para Hydro-V"
    )
    parser.add_argument(
        "--model",
        choices=["autonomy", "leaks", "all"],
        default="all",
        help="Qué modelo generar (default: all)",
    )
    parser.add_argument(
        "--save-data",
        action="store_true",
        help="Guardar también los datos sintéticos como CSV",
    )
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("  HYDRO-V — Generador de Modelos ML")
    log.info("=" * 60)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    if args.model in ("autonomy", "all"):
        log.info("\n[1/2] Modelo de Autonomía Hídrica (sklearn Ridge)")
        train_autonomy_model(save_data=args.save_data)

    if args.model in ("leaks", "all"):
        log.info("\n[2/2] Modelo de Detección de Fugas (PyTorch MLP)")
        train_leaks_model(save_data=args.save_data)

    log.info("\n" + "=" * 60)
    log.info("  ✅ Todos los modelos generados correctamente")
    log.info(f"  📁 Ubicación: {MODELS_DIR}")
    log.info("=" * 60)
    log.info("\nAhora puedes arrancar el backend:")
    log.info("  cd hydrov-backend && uvicorn app.main:app --reload")


if __name__ == "__main__":
    main()
