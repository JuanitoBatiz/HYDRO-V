# hydrov-ml/src/models/gnn_leak_detection.py
"""
Red Neuronal para detección de fugas en nodos Hydro-V.

Arquitectura: MLP simple (placeholder para la GNN real de Emma).
Entrada dinámica: [flow_lpm, level_pct] del nodo + vecinos.
Salida: escalar 0.0–1.0 (score de anomalía).

Cuando haya múltiples nodos, Emma implementará la GNN completa
con torch_geometric. Este modelo sirve como puente mientras tanto.

Input shape: (batch, 2 + 2*num_neighbors)
Output shape: (batch, 1)
"""
import torch
import torch.nn as nn


class LeakDetectorMLP(nn.Module):
    """
    MLP para detección de anomalías de flujo.

    Diseñado para funcionar con cualquier número de vecinos:
    - 0 vecinos: input_dim = 2  (solo nodo local)
    - 1 vecino:  input_dim = 4
    - N vecinos: input_dim = 2 + 2*N

    La capa de entrada es flexible — se adapta al tamaño del input
    en el forward pass mediante padding si es necesario.
    """

    # Dimensión máxima fija (nodo local + hasta 4 vecinos)
    MAX_INPUT_DIM = 10  # 2 + 2*4

    def __init__(self, hidden_dim: int = 32):
        super().__init__()

        self.network = nn.Sequential(
            nn.Linear(self.MAX_INPUT_DIM, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 1),
            nn.Sigmoid(),   # output entre 0 y 1
        )

        # Inicializar pesos con valores conservadores
        # (sesgo hacia "no fuga" para evitar falsos positivos)
        self._init_weights()

    def _init_weights(self):
        """Inicialización conservadora: scores cercanos a 0.1 (sin fuga)."""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight, gain=0.1)
                if module.bias is not None:
                    nn.init.constant_(module.bias, -2.0)  # sesgo hacia 0 inicial

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass con padding automático al MAX_INPUT_DIM.

        Args:
            x: Tensor de shape (batch, n_features) donde n_features puede variar.

        Returns:
            Tensor de shape (batch, 1) con scores de anomalía.
        """
        batch_size, n_features = x.shape

        # Padding con ceros si hay menos features que MAX_INPUT_DIM
        if n_features < self.MAX_INPUT_DIM:
            padding = torch.zeros(
                batch_size,
                self.MAX_INPUT_DIM - n_features,
                dtype=x.dtype,
                device=x.device,
            )
            x = torch.cat([x, padding], dim=1)
        elif n_features > self.MAX_INPUT_DIM:
            # Truncar si hay más vecinos de los esperados
            x = x[:, :self.MAX_INPUT_DIM]

        return self.network(x)


def build_model(hidden_dim: int = 32) -> LeakDetectorMLP:
    """
    Construye e inicializa el modelo de detección de fugas.
    Retorna el modelo en modo eval() listo para inferencia.
    """
    model = LeakDetectorMLP(hidden_dim=hidden_dim)
    model.eval()
    return model
