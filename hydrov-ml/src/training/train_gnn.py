# ============================================================
#  Hydro-V · Entrenamiento de la GNN
#  Archivo: src/training/train_gnn.py
# ============================================================
#
#  Ejecutar desde la raíz del proyecto hydrov-ml/:
#
#    python -m src.training.train_gnn
#
# ============================================================

from __future__ import annotations

import torch
import torch.nn.functional as F
from torch_geometric.data import Data
from sklearn.metrics import f1_score, precision_score, recall_score

from src.models.gnn_leak_detection import HydroGNN
from src.data.synthetic_generator import generar_red_completa, construir_grafo_instantaneo


# ── Hiperparámetros ──────────────────────────────────────────
EPOCHS = 200
LR = 0.001
HIDDEN_CH = 64
PATIENCE = 20          # Early stopping: parar si no mejora en 20 épocas
SAVE_PATH = "models/gnn_leak_detector_best.pth"


def _split_nodos(
    n: int, train_ratio: float = 0.70, val_ratio: float = 0.15
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Divide los nodos en conjuntos train / val / test."""
    idx = torch.randperm(n)
    t = int(n * train_ratio)
    v = int(n * (train_ratio + val_ratio))
    return idx[:t], idx[t:v], idx[v:]


def entrenar() -> None:
    print("=" * 55)
    print("  Hydro-V · Entrenamiento GNN")
    print("=" * 55)

    # ── 1. Generar datos y construir grafo ───────────────────
    print("\n[1/4] Generando datos sintéticos...")
    df_red = generar_red_completa(dias=60)

    print("[2/4] Construyendo grafo de la red...")
    grafo: Data = construir_grafo_instantaneo(df_red)
    n_nodos = grafo.num_nodes
    print(f"      Nodos: {n_nodos}  |  Aristas: {grafo.num_edges}")
    print(f"      Anomalías: {grafo.y.sum().item()}/{n_nodos}")

    # ── 2. Splits train / val / test ─────────────────────────
    idx_train, idx_val, idx_test = _split_nodos(n_nodos)

    # ── 3. Inicializar modelo, optimizador y loss ────────────
    print("[3/4] Iniciando entrenamiento...\n")
    modelo = HydroGNN(in_channels=grafo.num_node_features, hidden_ch=HIDDEN_CH)
    optimizador = torch.optim.Adam(modelo.parameters(), lr=LR)
    criterio = torch.nn.NLLLoss()

    mejor_val_loss = float("inf")
    epocas_sin_mejora = 0

    # ── 4. Loop de entrenamiento ─────────────────────────────
    for epoca in range(1, EPOCHS + 1):
        # --- Forward train ---
        modelo.train()
        optimizador.zero_grad()
        out = modelo(grafo.x, grafo.edge_index)
        loss_train = criterio(out[idx_train], grafo.y[idx_train])
        loss_train.backward()
        optimizador.step()

        # --- Forward val ---
        modelo.eval()
        with torch.no_grad():
            out_val = modelo(grafo.x, grafo.edge_index)
            loss_val = criterio(out_val[idx_val], grafo.y[idx_val])
            pred_val = out_val[idx_val].argmax(dim=1)
            acc_val = (pred_val == grafo.y[idx_val]).float().mean().item()

        # --- Log cada 10 épocas ---
        if epoca % 10 == 0 or epoca == 1:
            print(
                f"  Época {epoca:>3d}/{EPOCHS} | "
                f"Loss train: {loss_train:.4f} | "
                f"Loss val: {loss_val:.4f} | "
                f"Acc val: {acc_val:.3f}"
            )

        # --- Early stopping & checkpoint ---
        if loss_val < mejor_val_loss:
            mejor_val_loss = loss_val
            epocas_sin_mejora = 0
            torch.save(modelo.state_dict(), SAVE_PATH)
        else:
            epocas_sin_mejora += 1
            if epocas_sin_mejora >= PATIENCE:
                print(f"\n  Early stopping en época {epoca}.")
                break

    # ── 5. Evaluación final en test ──────────────────────────
    print("\n[4/4] Evaluación en conjunto de test...")
    modelo.load_state_dict(torch.load(SAVE_PATH))
    modelo.eval()

    with torch.no_grad():
        out_test = modelo(grafo.x, grafo.edge_index)
        pred_test = out_test[idx_test].argmax(dim=1).numpy()
        y_test = grafo.y[idx_test].numpy()

    acc = (pred_test == y_test).mean()
    prec = precision_score(y_test, pred_test, zero_division=0)
    rec = recall_score(y_test, pred_test, zero_division=0)
    f1 = f1_score(y_test, pred_test, zero_division=0)

    print(f"\n  Accuracy  : {acc:.4f}")
    print(f"  Precision : {prec:.4f}")
    print(f"  Recall    : {rec:.4f}")
    print(f"  F1-Score  : {f1:.4f}")
    print(f"\n  Modelo guardado en: {SAVE_PATH}")
    print("=" * 55)


if __name__ == "__main__":
    entrenar()