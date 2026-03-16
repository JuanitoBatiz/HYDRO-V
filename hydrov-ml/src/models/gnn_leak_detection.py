# ============================================================
#  Hydro-V · Detección de Fugas con Graph Neural Network
#  Archivo: src/models/gnn_leak_detection.py
#  Arquitectura: GraphSAGE (SAGEConv) — 3 capas
# ============================================================
#
#  NOTA: Este archivo es la ubicación correcta para el modelo GNN.
#  Si creaste un archivo separado llamado gnn_model.py, su contenido
#  debe vivir aquí. Elimina gnn_model.py del proyecto.
#
# ============================================================

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import SAGEConv


class HydroGNN(nn.Module):
    """
    Graph Neural Network para detección de fugas y anomalías en la
    red hídrica de Neza (50 nodos: 1 real + 49 sintéticos).

    Cada nodo representa un sensor Hydro-V con 8 características:
        [turbidez_norm, flujo_norm, nivel_norm, presion_est,
         delta_turbidez, delta_flujo, hora_sin, hora_cos]

    Las aristas codifican la conectividad hidráulica entre sensores
    vecinos (distancia < 500 m en la red municipal).

    Hipótesis de detección:
        Si el nodo A muestra caída de presión/flujo MIENTRAS sus
        vecinos B y C se mantienen normales → alta probabilidad
        de fuga en la tubería entre A-B o A-C.

    Arquitectura:
        SAGEConv(8 → 64) → ReLU → Dropout(0.3)
        SAGEConv(64 → 32) → ReLU → Dropout(0.3)
        SAGEConv(32 → 16) → ReLU
        Linear(16 → 8)   → ReLU
        Linear(8  → 2)   → log_softmax   [sin_fuga, con_fuga]

    Args:
        in_channels  (int): Número de features por nodo. Por defecto 8.
        hidden_ch    (int): Dimensión espacio latente capa 1. Por defecto 64.
        num_classes  (int): Clases de salida (2 = normal / anomalía).
    """

    def __init__(
        self,
        in_channels: int = 8,
        hidden_ch: int = 64,
        num_classes: int = 2,
    ) -> None:
        super().__init__()

        # Capas de convolución de grafos (GraphSAGE)
        self.conv1 = SAGEConv(in_channels, hidden_ch)
        self.conv2 = SAGEConv(hidden_ch, 32)
        self.conv3 = SAGEConv(32, 16)

        # Clasificador final (capas densas)
        self.fc1 = nn.Linear(16, 8)
        self.fc2 = nn.Linear(8, num_classes)

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        """
        Propagación hacia adelante.

        Args:
            x          : Matriz de features [num_nodos, in_channels].
                         Para la red completa: [50, 8].
            edge_index : Índices COO de aristas [2, num_aristas].

        Returns:
            Log-probabilidades por nodo [num_nodos, num_classes].
            Usar torch.exp() para obtener probabilidades reales.
        """
        # --- Capa 1: agrega información de vecinos directos ---
        x = self.conv1(x, edge_index)
        x = F.relu(x)
        x = F.dropout(x, p=0.3, training=self.training)

        # --- Capa 2: refina representación con segundo vecindario ---
        x = self.conv2(x, edge_index)
        x = F.relu(x)
        x = F.dropout(x, p=0.3, training=self.training)

        # --- Capa 3: consolida representación latente ---
        x = self.conv3(x, edge_index)
        x = F.relu(x)

        # --- Clasificador ---
        x = F.relu(self.fc1(x))
        x = self.fc2(x)

        return F.log_softmax(x, dim=1)