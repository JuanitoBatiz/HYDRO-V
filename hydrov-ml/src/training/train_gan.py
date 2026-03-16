# ============================================================
#  Hydro-V · Entrenamiento del GAN
#  Archivo: src/training/train_gan.py
# ============================================================
#
#  Ejecutar desde la raíz del proyecto hydrov-ml/:
#
#    python -m src.training.train_gan
#
#  El GAN aprende la distribución de los datos REALES del
#  nodo HYDRO-V-001 (cuando estén disponibles) para luego
#  generar los 49 nodos sintéticos de forma más realista.
#
#  Por ahora, entrena con datos sintéticos de muestra.
#  Cuando el ESP32 esté operativo, reemplazar datos_reales()
#  con la carga desde InfluxDB o CSV.
#
# ============================================================

from __future__ import annotations

import torch
import torch.nn as nn
import numpy as np
import pandas as pd

from src.models.gan_synthetic import Generator, Discriminator, NOISE_DIM, FEATURE_DIM
from src.data.synthetic_generator import generar_datos_nodo


# ── Hiperparámetros ──────────────────────────────────────────
EPOCHS = 500           # Para el concurso: 500 es suficiente. Paper usa 10,000
BATCH_SIZE = 64
LR = 0.0002
BETAS = (0.5, 0.999)
SAVE_PATH_GEN = "models/gan_generator_best.pth"


def _cargar_datos_reales() -> torch.Tensor:
    """
    Carga datos reales del nodo HYDRO-V-001.

    FASE ACTUAL (sin hardware): usa nodo sintético 2 como proxy.
    FASE PRODUCCIÓN: reemplazar por carga desde InfluxDB/CSV.

    Returns:
        Tensor [n_muestras, 8] normalizado a [-1, 1].
    """
    print("  [AVISO] Usando datos sintéticos como proxy del nodo real.")
    print("  [AVISO] Reemplazar con datos reales del ESP32 cuando estén disponibles.")

    df = generar_datos_nodo(node_id=2, dias=60, seed=0)

    feature_cols = [
        "turbidity_ntu", "flow_lpm", "distance_cm", "flow_total",
        "hora_sin", "hora_cos", "dia_sin", "dia_cos",
    ]

    X = df[feature_cols].values.astype(np.float32)

    # Normalizar a [-1, 1] para que sea compatible con la salida Tanh del generador
    X_min = X.min(axis=0, keepdims=True)
    X_max = X.max(axis=0, keepdims=True)
    rango = (X_max - X_min).clip(min=1e-6)
    X_norm = 2 * (X - X_min) / rango - 1

    return torch.tensor(X_norm, dtype=torch.float32)


def entrenar() -> None:
    print("=" * 55)
    print("  Hydro-V · Entrenamiento GAN")
    print("=" * 55)

    # ── 1. Cargar datos reales ───────────────────────────────
    print("\n[1/3] Cargando datos de entrenamiento...")
    datos_reales = _cargar_datos_reales()
    n_total = len(datos_reales)
    print(f"      Muestras: {n_total:,}  |  Features: {FEATURE_DIM}")

    # ── 2. Inicializar modelos ───────────────────────────────
    generador = Generator(noise_dim=NOISE_DIM, output_dim=FEATURE_DIM)
    discriminador = Discriminator(input_dim=FEATURE_DIM)

    criterio = nn.BCELoss()
    opt_G = torch.optim.Adam(generador.parameters(), lr=LR, betas=BETAS)
    opt_D = torch.optim.Adam(discriminador.parameters(), lr=LR, betas=BETAS)

    labels_reales = torch.ones(BATCH_SIZE, 1)
    labels_falsos = torch.zeros(BATCH_SIZE, 1)

    # ── 3. Loop de entrenamiento ─────────────────────────────
    print(f"[2/3] Entrenando {EPOCHS} épocas...\n")

    for epoca in range(1, EPOCHS + 1):
        # Seleccionar batch aleatorio de datos reales
        idx = torch.randint(0, n_total, (BATCH_SIZE,))
        reales = datos_reales[idx]

        # ---------- Entrenar Discriminador ----------
        opt_D.zero_grad()

        ruido = torch.randn(BATCH_SIZE, NOISE_DIM)
        falsos = generador(ruido).detach()

        loss_D_real = criterio(discriminador(reales), labels_reales)
        loss_D_fake = criterio(discriminador(falsos), labels_falsos)
        loss_D = loss_D_real + loss_D_fake

        loss_D.backward()
        opt_D.step()

        # ---------- Entrenar Generador ----------
        opt_G.zero_grad()

        ruido = torch.randn(BATCH_SIZE, NOISE_DIM)
        falsos = generador(ruido)
        # El generador quiere engañar al discriminador (clasificar como 1)
        loss_G = criterio(discriminador(falsos), labels_reales)

        loss_G.backward()
        opt_G.step()

        if epoca % 50 == 0 or epoca == 1:
            print(
                f"  Época {epoca:>4d}/{EPOCHS} | "
                f"Loss D: {loss_D:.4f} | "
                f"Loss G: {loss_G:.4f}"
            )

    # ── 4. Guardar generador ─────────────────────────────────
    print(f"\n[3/3] Guardando generador en: {SAVE_PATH_GEN}")
    torch.save(generador.state_dict(), SAVE_PATH_GEN)
    print("  Entrenamiento GAN completado.")
    print("=" * 55)


if __name__ == "__main__":
    entrenar()