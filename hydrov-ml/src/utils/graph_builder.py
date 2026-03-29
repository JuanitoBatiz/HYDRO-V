# ============================================================
#  Hydro-V · Constructor de Grafos de la Red Hídrica
#  Archivo: src/utils/graph_builder.py
# ============================================================

from __future__ import annotations

import torch
import numpy as np
import pandas as pd
from torch_geometric.data import Data


def construir_edge_index_por_distancia(
    coords: list[tuple[float, float]],
    radio_m: float = 500.0,
) -> torch.Tensor:
    """
    Conecta nodos cuya distancia geográfica sea menor a radio_m metros.

    Cuando el hardware esté operativo y los nodos tengan coordenadas
    GPS reales (latitud/longitud de las colonias de Neza), esta función
    construirá la topología real de la red.

    Args:
        coords  : Lista de (latitud, longitud) por nodo.
        radio_m : Radio de conexión en metros. Por defecto 500 m.

    Returns:
        edge_index: Tensor COO [2, num_aristas] bidireccional.
    """
    n = len(coords)
    src, dst = [], []

    for i in range(n):
        for j in range(i + 1, n):
            d = _distancia_haversine_m(coords[i], coords[j])
            if d < radio_m:
                src.extend([i, j])
                dst.extend([j, i])

    if not src:
        # Sin aristas: conectar en anillo mínimo para evitar grafos vacíos
        for i in range(n):
            j = (i + 1) % n
            src.extend([i, j])
            dst.extend([j, i])

    return torch.tensor([src, dst], dtype=torch.long)


def construir_edge_index_anillo(n_nodos: int, saltos: list[int] = None) -> torch.Tensor:
    """
    Crea una topología en anillo con saltos opcionales.

    Útil para los datos sintéticos donde no tenemos coordenadas GPS reales
    pero queremos una conectividad hidráulica plausible.

    Args:
        n_nodos : Número de nodos en el grafo.
        saltos  : Lista de offsets de conexión. Por defecto [1, 2, 5].

    Returns:
        edge_index: Tensor COO [2, num_aristas].
    """
    if saltos is None:
        saltos = [1, 2, 5]

    src, dst = [], []
    for i in range(n_nodos):
        for offset in saltos:
            j = (i + offset) % n_nodos
            src.extend([i, j])
            dst.extend([j, i])

    return torch.tensor([src, dst], dtype=torch.long)


def _distancia_haversine_m(
    coord1: tuple[float, float],
    coord2: tuple[float, float],
) -> float:
    """
    Calcula la distancia en metros entre dos coordenadas GPS
    usando la fórmula de Haversine.

    Args:
        coord1, coord2: (latitud, longitud) en grados decimales.

    Returns:
        Distancia en metros.
    """
    R = 6_371_000  # Radio de la Tierra en metros
    lat1, lon1 = np.radians(coord1)
    lat2, lon2 = np.radians(coord2)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    return R * c