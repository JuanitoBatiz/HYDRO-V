# ============================================================
#  Hydro-V · Detección de Fugas con Graph Neural Network
#  Archivo: src/models/gnn_leak_detection.py
#  Arquitectura: GraphSAGE (SAGEConv) — 3 capas
# ============================================================

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import SAGEConv


class HydroGNN(nn.Module):
    """
    Graph Neural Network para detección de fugas en la red hídrica.

    Cada nodo representa un sensor Hydro-V con 8 características:
        [turbidez_norm, flujo_norm, nivel_norm, presion_est,
         delta_turbidez, delta_flujo, hora_sin, hora_cos]

    Las aristas representan conectividad hidráulica entre nodos.

    Arquitectura:
        SAGEConv(8 → 64) → ReLU → Dropout(0.3)
        SAGEConv(64 → 32) → ReLU → Dropout(0.3)
        SAGEConv(32 → 16) → ReLU
        Linear(16 → 8)   → ReLU
        Linear(8  → 2)   → log_softmax
    """

    def __init__(
        self,
        in_channels: int = 8,
        hidden_ch: int = 64,
        num_classes: int = 2,
        dropout: float = 0.3,
    ) -> None:
        super().__init__()

        # ── GNN Layers (GraphSAGE) ────────────────────────────
        self.conv1 = SAGEConv(in_channels, hidden_ch)
        self.conv2 = SAGEConv(hidden_ch, 32)
        self.conv3 = SAGEConv(32, 16)

        # ── Fully Connected Layers ────────────────────────────
        self.fc1 = nn.Linear(16, 8)
        self.fc2 = nn.Linear(8, num_classes)

        self.dropout = dropout

        self._init_weights()

    # ── Inicialización de pesos ───────────────────────────────
    def _init_weights(self):
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)

    # ── Forward pass ──────────────────────────────────────────
    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor
    ) -> torch.Tensor:
        """
        Args:
            x: [num_nodos, in_channels]
            edge_index: [2, num_aristas]

        Returns:
            log-probabilidades [num_nodos, num_classes]
        """

        # ── Capa 1 ────────────────────────────────────────────
        x = self.conv1(x, edge_index)
        x = F.relu(x)
        x = F.dropout(x, p=self.dropout, training=self.training)

        # ── Capa 2 ────────────────────────────────────────────
        x = self.conv2(x, edge_index)
        x = F.relu(x)
        x = F.dropout(x, p=self.dropout, training=self.training)

        # ── Capa 3 ────────────────────────────────────────────
        x = self.conv3(x, edge_index)
        x = F.relu(x)

        # ── Clasificador ──────────────────────────────────────
        x = F.relu(self.fc1(x))
        x = self.fc2(x)

        return F.log_softmax(x, dim=1)


# ── Test rápido ───────────────────────────────────────────────
if __name__ == "__main__":
    print("🧠 Test rápido de HydroGNN")

    num_nodos = 10
    num_features = 8

    # Features aleatorias
    x = torch.rand((num_nodos, num_features))

    # Grafo simple (cadena)
    edge_index = torch.tensor([
        [0, 1, 2, 3, 4, 5, 6, 7, 8],
        [1, 2, 3, 4, 5, 6, 7, 8, 9]
    ], dtype=torch.long)

    model = HydroGNN()
    model.eval()

    with torch.no_grad():
        out = model(x, edge_index)

    print("Output shape:", out.shape)  # [num_nodos, 2]
    print("Ejemplo salida:", out[0])