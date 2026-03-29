# ============================================================
#  Hydro-V · GAN para Generación de Datos Sintéticos
#  Archivo: src/models/gan_synthetic.py
#  Framework: PyTorch
# ============================================================
#
#  Genera datos sintéticos de sensores para los 49 nodos
#  virtuales de la red hídrica de Neza.
#
#  El Generador aprende la distribución de datos reales del
#  nodo HYDRO-V-001 y produce lecturas realistas para los
#  nodos 002–050.
#
# ============================================================

import torch
import torch.nn as nn


# ── Dimensiones del dataset ──────────────────────────────────
# Cada muestra tiene 8 features que coinciden con la telemetría
# que publica el ESP32 vía MQTT:
#   [turbidez_ntu, flujo_lpm, distancia_cm, flujo_total,
#    hora_sin, hora_cos, dia_sin, dia_cos]
FEATURE_DIM = 8
NOISE_DIM = 100   # Dimensión del vector de ruido de entrada al generador


class Generator(nn.Module):
    """
    Genera muestras de sensores sintéticos a partir de ruido aleatorio.

    Arquitectura:
        Linear(100 → 256)  → BN → LeakyReLU
        Linear(256 → 512)  → BN → LeakyReLU
        Linear(512 → 1024) → BN → LeakyReLU
        Linear(1024 → 8)   → Tanh   (salida normalizada [-1, 1])

    Args:
        noise_dim  (int): Dimensión del vector de ruido. Por defecto 100.
        output_dim (int): Número de features a generar. Por defecto 8.
    """

    def __init__(self, noise_dim: int = NOISE_DIM, output_dim: int = FEATURE_DIM) -> None:
        super().__init__()

        self.model = nn.Sequential(
            # Bloque 1
            nn.Linear(noise_dim, 256),
            nn.BatchNorm1d(256),
            nn.LeakyReLU(0.2, inplace=True),

            # Bloque 2
            nn.Linear(256, 512),
            nn.BatchNorm1d(512),
            nn.LeakyReLU(0.2, inplace=True),

            # Bloque 3
            nn.Linear(512, 1024),
            nn.BatchNorm1d(1024),
            nn.LeakyReLU(0.2, inplace=True),

            # Capa de salida — Tanh normaliza a [-1, 1]
            # Se desnormaliza al guardar los datos finales
            nn.Linear(1024, output_dim),
            nn.Tanh(),
        )

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        """
        Args:
            z: Vector de ruido [batch_size, noise_dim].
        Returns:
            Muestra sintética [batch_size, output_dim].
        """
        return self.model(z)


class Discriminator(nn.Module):
    """
    Clasifica si una muestra de sensor es real (del ESP32) o sintética.

    Arquitectura:
        Linear(8 → 512)  → LeakyReLU → Dropout(0.3)
        Linear(512 → 256) → LeakyReLU → Dropout(0.3)
        Linear(256 → 128) → LeakyReLU
        Linear(128 → 1)   → Sigmoid   (probabilidad real/falso)

    Args:
        input_dim (int): Número de features de entrada. Por defecto 8.
    """

    def __init__(self, input_dim: int = FEATURE_DIM) -> None:
        super().__init__()

        self.model = nn.Sequential(
            # Bloque 1
            nn.Linear(input_dim, 512),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Dropout(0.3),

            # Bloque 2
            nn.Linear(512, 256),
            nn.LeakyReLU(0.2, inplace=True),
            nn.Dropout(0.3),

            # Bloque 3
            nn.Linear(256, 128),
            nn.LeakyReLU(0.2, inplace=True),

            # Salida: probabilidad de ser real
            nn.Linear(128, 1),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Muestra de sensor [batch_size, input_dim].
        Returns:
            Probabilidad de ser real [batch_size, 1].
        """
        return self.model(x)