# ============================================================
#  Hydro-V · Visualizaciones para el Concurso
#  Archivo: src/utils/visualization.py
#
#  Genera 6 gráficas con estilo NASA/Control Center que
#  demuestran el funcionamiento del sistema ante el jurado.
#
#  Ejecutar desde hydrov-ml/:
#    python -m src.utils.visualization
#
#  Guarda las imágenes en: reports/figures/
# ============================================================

from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.colors import LinearSegmentedColormap
import networkx as nx

# ── Directorio de salida ──────────────────────────────────────
FIGURES_DIR = Path("reports/figures")
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

# ── Paleta NASA / Mission Control ────────────────────────────
NASA = {
    "bg":        "#050d1a",   # Fondo principal (azul noche)
    "bg2":       "#0a1628",   # Fondo tarjetas
    "grid":      "#0f2040",   # Líneas de cuadrícula
    "cyan":      "#00d4ff",   # Acento principal
    "green":     "#00ff9d",   # Normal / OK
    "red":       "#ff3c5a",   # Anomalía / Alerta
    "yellow":    "#ffd600",   # Advertencia
    "purple":    "#b56aff",   # Secundario
    "text":      "#c8dff5",   # Texto principal
    "subtext":   "#4a7099",   # Texto secundario
    "white":     "#e8f4ff",   # Títulos
}

# ── Configuración global de matplotlib ───────────────────────
plt.rcParams.update({
    "figure.facecolor":  NASA["bg"],
    "axes.facecolor":    NASA["bg2"],
    "axes.edgecolor":    NASA["grid"],
    "axes.labelcolor":   NASA["text"],
    "axes.titlecolor":   NASA["white"],
    "axes.titlesize":    11,
    "axes.labelsize":    9,
    "axes.grid":         True,
    "grid.color":        NASA["grid"],
    "grid.linewidth":    0.6,
    "xtick.color":       NASA["subtext"],
    "ytick.color":       NASA["subtext"],
    "xtick.labelsize":   8,
    "ytick.labelsize":   8,
    "text.color":        NASA["text"],
    "legend.facecolor":  NASA["bg"],
    "legend.edgecolor":  NASA["grid"],
    "legend.fontsize":   8,
    "font.family":       "monospace",
    "lines.linewidth":   1.8,
})


# ════════════════════════════════════════════════════════════
#  GRÁFICA 1 — CURVAS DE ENTRENAMIENTO GNN
# ════════════════════════════════════════════════════════════

def plot_training_curves(
    train_losses: list[float],
    val_losses: list[float],
    val_accuracies: list[float],
    save: bool = True,
) -> plt.Figure:
    """
    Muestra loss de train/val y accuracy de validación por época.
    Marca el punto de early stopping con una línea vertical.

    Args:
        train_losses   : Loss de entrenamiento por época.
        val_losses     : Loss de validación por época.
        val_accuracies : Accuracy de validación por época.
        save           : Si True, guarda la imagen en reports/figures/.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.5))
    fig.suptitle(
        "HYDRO-V  ·  GNN TRAINING METRICS",
        color=NASA["cyan"], fontsize=13, fontweight="bold", y=1.01,
        fontfamily="monospace",
    )

    epochs = range(1, len(train_losses) + 1)
    mejor_epoca = int(np.argmin(val_losses)) + 1

    # --- Panel izquierdo: Loss ---
    ax1.plot(epochs, train_losses, color=NASA["cyan"],  label="Train loss",  alpha=0.9)
    ax1.plot(epochs, val_losses,   color=NASA["yellow"], label="Val loss", alpha=0.9,
             linestyle="--")
    ax1.axvline(mejor_epoca, color=NASA["green"], linewidth=1.2,
                linestyle=":", alpha=0.8, label=f"Best epoch ({mejor_epoca})")
    ax1.fill_between(epochs, train_losses, val_losses,
                     alpha=0.08, color=NASA["cyan"])
    ax1.set_title("Loss por época", pad=8)
    ax1.set_xlabel("Época")
    ax1.set_ylabel("NLL Loss")
    ax1.legend()

    # Anotación del mínimo
    min_val = min(val_losses)
    ax1.annotate(
        f" min val: {min_val:.4f}",
        xy=(mejor_epoca, min_val),
        color=NASA["green"], fontsize=8,
        arrowprops=dict(arrowstyle="->", color=NASA["green"], lw=0.8),
        xytext=(mejor_epoca + len(epochs) * 0.08, min_val + 0.02),
    )

    # --- Panel derecho: Accuracy ---
    ax2.plot(epochs, val_accuracies, color=NASA["green"], label="Val accuracy")
    ax2.fill_between(epochs, val_accuracies, alpha=0.15, color=NASA["green"])
    ax2.axhline(max(val_accuracies), color=NASA["purple"], linewidth=1,
                linestyle=":", alpha=0.7,
                label=f"Max acc: {max(val_accuracies):.3f}")
    ax2.set_ylim(0, 1.05)
    ax2.set_title("Accuracy de validación", pad=8)
    ax2.set_xlabel("Época")
    ax2.set_ylabel("Accuracy")
    ax2.legend()

    # Watermark del sistema
    fig.text(0.99, 0.01, "HYDRO-V MISSION CONTROL · GNN MODULE",
             ha="right", va="bottom", fontsize=7,
             color=NASA["subtext"], alpha=0.6)

    plt.tight_layout()
    if save:
        path = FIGURES_DIR / "01_training_curves.png"
        fig.savefig(path, dpi=150, bbox_inches="tight",
                    facecolor=NASA["bg"])
        print(f"[Viz] Guardado: {path}")
    return fig


# ════════════════════════════════════════════════════════════
#  GRÁFICA 2 — MATRIZ DE CONFUSIÓN
# ════════════════════════════════════════════════════════════

def plot_confusion_matrix(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    save: bool = True,
) -> plt.Figure:
    """
    Matriz de confusión con métricas clave integradas.

    Args:
        y_true: Etiquetas reales.
        y_pred: Predicciones del modelo.
        save  : Si True, guarda la imagen.
    """
    from sklearn.metrics import confusion_matrix, classification_report

    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel()

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1        = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    accuracy  = (tp + tn) / cm.sum()

    fig = plt.figure(figsize=(10, 5.5))
    gs  = gridspec.GridSpec(1, 2, width_ratios=[1.2, 1], wspace=0.35)

    # --- Panel izquierdo: Heatmap ---
    ax_cm = fig.add_subplot(gs[0])

    cmap = LinearSegmentedColormap.from_list(
        "hydrov", [NASA["bg2"], NASA["cyan"]], N=256
    )
    im = ax_cm.imshow(cm, cmap=cmap, aspect="auto")

    labels = [["TN", "FP"], ["FN", "TP"]]
    colors_text = [[NASA["text"], NASA["red"]], [NASA["red"], NASA["green"]]]

    for i in range(2):
        for j in range(2):
            ax_cm.text(
                j, i,
                f"{labels[i][j]}\n{cm[i, j]}",
                ha="center", va="center",
                fontsize=14, fontweight="bold",
                color=colors_text[i][j],
            )

    ax_cm.set_xticks([0, 1])
    ax_cm.set_yticks([0, 1])
    ax_cm.set_xticklabels(["Normal (pred)", "Anomalía (pred)"],
                          color=NASA["text"], fontsize=8)
    ax_cm.set_yticklabels(["Normal (real)", "Anomalía (real)"],
                          color=NASA["text"], fontsize=8, rotation=90, va="center")
    ax_cm.set_title("Matriz de Confusión — GNN", pad=10)
    ax_cm.grid(False)

    # --- Panel derecho: Métricas ---
    ax_m = fig.add_subplot(gs[1])
    ax_m.axis("off")

    metricas = [
        ("ACCURACY",  accuracy,  NASA["cyan"]),
        ("PRECISION", precision, NASA["purple"]),
        ("RECALL",    recall,    NASA["yellow"]),
        ("F1-SCORE",  f1,        NASA["green"]),
    ]

    ax_m.text(0.5, 1.0, "MÉTRICAS DEL MODELO",
              ha="center", va="top", fontsize=10, fontweight="bold",
              color=NASA["white"], transform=ax_m.transAxes)

    for idx, (nombre, valor, color) in enumerate(metricas):
        y_pos = 0.82 - idx * 0.20
        # Barra de progreso
        ax_m.barh(y_pos, valor, height=0.10, left=0,
                  color=color, alpha=0.25, transform=ax_m.transAxes)
        ax_m.barh(y_pos, valor, height=0.10, left=0,
                  color=color, alpha=0.80, transform=ax_m.transAxes,
                  linewidth=0)
        ax_m.text(-0.02, y_pos, nombre,
                  ha="right", va="center", fontsize=8,
                  color=NASA["text"], transform=ax_m.transAxes)
        ax_m.text(valor + 0.02, y_pos, f"{valor:.3f}",
                  ha="left", va="center", fontsize=10, fontweight="bold",
                  color=color, transform=ax_m.transAxes)

    fig.suptitle("HYDRO-V  ·  GNN CLASSIFICATION RESULTS",
                 color=NASA["cyan"], fontsize=13, fontweight="bold",
                 fontfamily="monospace")
    fig.text(0.99, 0.01, "HYDRO-V MISSION CONTROL · GNN MODULE",
             ha="right", va="bottom", fontsize=7,
             color=NASA["subtext"], alpha=0.6)

    plt.tight_layout()
    if save:
        path = FIGURES_DIR / "02_confusion_matrix.png"
        fig.savefig(path, dpi=150, bbox_inches="tight",
                    facecolor=NASA["bg"])
        print(f"[Viz] Guardado: {path}")
    return fig


# ════════════════════════════════════════════════════════════
#  GRÁFICA 3 — GRAFO DE LA RED HÍDRICA
# ════════════════════════════════════════════════════════════

def plot_network_graph(
    edge_index: np.ndarray,
    anomaly_probs: np.ndarray,
    node_labels: np.ndarray | None = None,
    save: bool = True,
) -> plt.Figure:
    """
    Visualiza la red hídrica como grafo. Los nodos se colorean
    por probabilidad de anomalía — de azul (normal) a rojo (fuga).

    Args:
        edge_index    : Array [2, E] con las aristas del grafo.
        anomaly_probs : Probabilidad de anomalía por nodo [N].
        node_labels   : Etiquetas reales (0/1) para marcar TN/TP/FP/FN.
        save          : Si True, guarda la imagen.
    """
    n_nodos = len(anomaly_probs)
    G = nx.Graph()
    G.add_nodes_from(range(n_nodos))

    # Añadir aristas (deduplicadas)
    aristas = set()
    for i in range(edge_index.shape[1]):
        u, v = int(edge_index[0, i]), int(edge_index[1, i])
        if u != v:
            aristas.add((min(u, v), max(u, v)))
    G.add_edges_from(aristas)

    # Layout en espiral para simular distribución urbana de Neza
    pos = nx.spring_layout(G, seed=42, k=0.6)

    fig, ax = plt.subplots(figsize=(12, 8))
    fig.suptitle(
        "HYDRO-V  ·  RED HÍDRICA NEZA  —  ANOMALY DETECTION MAP",
        color=NASA["cyan"], fontsize=13, fontweight="bold",
        fontfamily="monospace",
    )

    # Colormap: cyan → amarillo → rojo
    cmap_nodos = LinearSegmentedColormap.from_list(
        "anomaly", [NASA["cyan"], NASA["yellow"], NASA["red"]], N=256
    )
    colores_nodos = [cmap_nodos(p) for p in anomaly_probs]

    # Tamaño proporcional a la probabilidad
    tamaños = 80 + 320 * anomaly_probs

    # Dibujar aristas tenues
    nx.draw_networkx_edges(
        G, pos, ax=ax, alpha=0.18,
        edge_color=NASA["grid"], width=0.8,
    )

    # Dibujar nodos
    sc = nx.draw_networkx_nodes(
        G, pos, ax=ax,
        node_color=anomaly_probs,
        cmap=cmap_nodos,
        node_size=tamaños,
        vmin=0, vmax=1,
        linewidths=0.5,
    )

    # Resaltar nodos con alta probabilidad (> 0.75)
    nodos_alerta = [i for i, p in enumerate(anomaly_probs) if p > 0.75]
    if nodos_alerta:
        nx.draw_networkx_nodes(
            G, pos, nodelist=nodos_alerta, ax=ax,
            node_color="none",
            edgecolors=NASA["red"],
            node_size=[tamaños[i] * 1.6 for i in nodos_alerta],
            linewidths=2.0,
        )

    # Nodo real (HYDRO-V-001) marcado con estrella
    nx.draw_networkx_nodes(
        G, pos, nodelist=[0], ax=ax,
        node_color=NASA["white"],
        node_shape="*",
        node_size=400,
        linewidths=1.5,
    )
    ax.annotate("HYDRO-V-001\n(nodo real)",
                xy=pos[0], xytext=(pos[0][0] + 0.08, pos[0][1] + 0.08),
                color=NASA["white"], fontsize=7,
                arrowprops=dict(arrowstyle="->", color=NASA["white"], lw=0.7))

    # Colorbar
    sm = plt.cm.ScalarMappable(cmap=cmap_nodos, norm=plt.Normalize(0, 1))
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, shrink=0.7, pad=0.02)
    cbar.set_label("Probabilidad de anomalía", color=NASA["text"], fontsize=8)
    cbar.ax.yaxis.set_tick_params(color=NASA["subtext"])
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color=NASA["text"], fontsize=7)

    # Leyenda
    leyenda = [
        mpatches.Patch(color=NASA["cyan"],   label="Normal  (prob < 0.25)"),
        mpatches.Patch(color=NASA["yellow"], label="Sospecho (0.25–0.75)"),
        mpatches.Patch(color=NASA["red"],    label="Anomalía (prob > 0.75)"),
        mpatches.Patch(color=NASA["white"],  label="Nodo real HYDRO-V-001"),
    ]
    ax.legend(handles=leyenda, loc="lower right", fontsize=8,
              facecolor=NASA["bg"], edgecolor=NASA["grid"])

    ax.set_axis_off()
    ax.set_facecolor(NASA["bg"])

    # Stats overlay
    n_anomalias = (anomaly_probs > 0.75).sum()
    ax.text(0.01, 0.99,
            f"NODOS ACTIVOS : {n_nodos}\n"
            f"ALERTAS       : {n_anomalias}\n"
            f"ARISTAS       : {len(aristas)}",
            transform=ax.transAxes, va="top", ha="left",
            fontsize=8, color=NASA["cyan"],
            fontfamily="monospace",
            bbox=dict(boxstyle="round,pad=0.4", facecolor=NASA["bg2"],
                      edgecolor=NASA["grid"], alpha=0.9))

    fig.text(0.99, 0.01, "HYDRO-V MISSION CONTROL · NETWORK INTELLIGENCE",
             ha="right", va="bottom", fontsize=7,
             color=NASA["subtext"], alpha=0.6)

    plt.tight_layout()
    if save:
        path = FIGURES_DIR / "03_network_graph.png"
        fig.savefig(path, dpi=150, bbox_inches="tight",
                    facecolor=NASA["bg"])
        print(f"[Viz] Guardado: {path}")
    return fig


# ════════════════════════════════════════════════════════════
#  GRÁFICA 4 — DISTRIBUCIÓN DE TURBIDEZ
# ════════════════════════════════════════════════════════════

def plot_turbidity_distribution(
    df_red: pd.DataFrame,
    save: bool = True,
) -> plt.Figure:
    """
    Histograma de turbidez con líneas de umbral del sistema:
    - Verde : < 50 NTU  (agua limpia, admitir)
    - Amarillo: 50–200 NTU (analizar)
    - Rojo  : > 200 NTU (rechazar / anomalía)

    Args:
        df_red: DataFrame de la red completa (synthetic_generator).
        save  : Si True, guarda la imagen.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.5))
    fig.suptitle(
        "HYDRO-V  ·  TURBIDITY DISTRIBUTION ANALYSIS",
        color=NASA["cyan"], fontsize=13, fontweight="bold",
        fontfamily="monospace",
    )

    turbidez = df_red["turbidity_ntu"].values

    # --- Panel izquierdo: Histograma global ---
    bins = np.linspace(0, turbidez.max(), 80)
    counts, edges = np.histogram(turbidez, bins=bins)

    # Colorear barras según zona
    for i in range(len(counts)):
        mid = (edges[i] + edges[i + 1]) / 2
        if mid < 50:
            color = NASA["green"]
        elif mid < 200:
            color = NASA["yellow"]
        else:
            color = NASA["red"]
        ax1.bar(edges[i], counts[i], width=edges[i+1]-edges[i],
                align="edge", color=color, alpha=0.75)

    ax1.axvline(50,  color=NASA["green"],  lw=1.5, linestyle="--",
                label="50 NTU — Umbral admisión")
    ax1.axvline(200, color=NASA["red"],    lw=1.5, linestyle="--",
                label="200 NTU — Umbral anomalía")
    ax1.set_title("Distribución global (49 nodos × 60 días)", pad=8)
    ax1.set_xlabel("Turbidez (NTU)")
    ax1.set_ylabel("Frecuencia")
    ax1.legend()

    # Stats integradas
    pct_limpia   = (turbidez < 50).mean() * 100
    pct_media    = ((turbidez >= 50) & (turbidez < 200)).mean() * 100
    pct_anomalia = (turbidez >= 200).mean() * 100

    ax1.text(0.98, 0.97,
             f"Limpia   : {pct_limpia:.1f}%\n"
             f"Análisis : {pct_media:.1f}%\n"
             f"Anomalía : {pct_anomalia:.1f}%",
             transform=ax1.transAxes, va="top", ha="right",
             fontsize=8, color=NASA["text"], fontfamily="monospace",
             bbox=dict(boxstyle="round,pad=0.4", facecolor=NASA["bg2"],
                       edgecolor=NASA["grid"], alpha=0.9))

    # --- Panel derecho: Por colonia ---
    colonias = df_red.groupby("device_id")["turbidity_ntu"].mean().values
    colonias_sorted = np.sort(colonias)
    ids = range(len(colonias_sorted))

    colores_barras = [
        NASA["green"]  if v < 50  else
        NASA["yellow"] if v < 200 else
        NASA["red"]
        for v in colonias_sorted
    ]

    ax2.barh(list(ids), colonias_sorted, color=colores_barras, alpha=0.8)
    ax2.axvline(50,  color=NASA["green"],  lw=1.2, linestyle="--", alpha=0.7)
    ax2.axvline(200, color=NASA["red"],    lw=1.2, linestyle="--", alpha=0.7)
    ax2.set_title("Turbidez media por nodo (ordenada)", pad=8)
    ax2.set_xlabel("Turbidez promedio (NTU)")
    ax2.set_ylabel("Nodo (ordenado)")
    ax2.set_yticks([])

    fig.text(0.99, 0.01, "HYDRO-V MISSION CONTROL · DATA ANALYTICS",
             ha="right", va="bottom", fontsize=7,
             color=NASA["subtext"], alpha=0.6)

    plt.tight_layout()
    if save:
        path = FIGURES_DIR / "04_turbidity_distribution.png"
        fig.savefig(path, dpi=150, bbox_inches="tight",
                    facecolor=NASA["bg"])
        print(f"[Viz] Guardado: {path}")
    return fig


# ════════════════════════════════════════════════════════════
#  GRÁFICA 5 — LÍNEA DE TIEMPO DE TURBIDEZ CON ANOMALÍAS
# ════════════════════════════════════════════════════════════

def plot_turbidity_timeline(
    df_nodo: pd.DataFrame,
    device_id: str = "HYDRO-V-002",
    save: bool = True,
) -> plt.Figure:
    """
    Muestra la turbidez de un nodo en el tiempo y resalta las
    zonas donde el sistema FSM activaría la válvula de rechazo.

    Esta gráfica es CLAVE para el concurso: muestra cómo el
    sistema decide de forma autónoma qué agua admitir.

    Args:
        df_nodo   : DataFrame de un solo nodo.
        device_id : ID del dispositivo para el título.
        save      : Si True, guarda la imagen.
    """
    df = df_nodo.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")

    # Submuestra para legibilidad (1 punto cada 30 min)
    # select_dtypes excluye device_id (str) para que resample().mean() no falle
    df_num = df.select_dtypes(include="number")
    df_plot = df_num.resample("30min").mean() if isinstance(df.index, pd.DatetimeIndex) else df_num.iloc[::6]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 7), sharex=True,
                                    gridspec_kw={"height_ratios": [2.5, 1]})
    fig.suptitle(
        f"HYDRO-V  ·  SENSOR TIMELINE  —  {device_id}",
        color=NASA["cyan"], fontsize=13, fontweight="bold",
        fontfamily="monospace",
    )

    t = df_plot.index if hasattr(df_plot.index, "__len__") else range(len(df_plot))
    turb = df_plot["turbidity_ntu"].values
    label_vals = df_plot["label"].values if "label" in df_plot.columns else (turb > 200).astype(int)

    # --- Panel superior: Turbidez ---
    ax1.plot(t, turb, color=NASA["cyan"], linewidth=1.2, alpha=0.9, label="Turbidez (NTU)")

    # Zonas de anomalía sombreadas
    en_anomalia = False
    inicio = None
    for i, (ts, lbl) in enumerate(zip(t, label_vals)):
        if lbl == 1 and not en_anomalia:
            inicio = ts
            en_anomalia = True
        elif lbl == 0 and en_anomalia:
            ax1.axvspan(inicio, ts, alpha=0.20, color=NASA["red"],
                        label="Zona rechazo (FSM)")
            en_anomalia = False
    if en_anomalia:
        ax1.axvspan(inicio, t[-1], alpha=0.20, color=NASA["red"])

    ax1.axhline(50,  color=NASA["green"],  lw=1.2, linestyle="--", alpha=0.7,
                label="50 NTU (admisión)")
    ax1.axhline(200, color=NASA["red"],    lw=1.2, linestyle="--", alpha=0.7,
                label="200 NTU (rechazo)")

    # Evitar duplicados en leyenda
    handles, labels_leg = ax1.get_legend_handles_labels()
    seen = set()
    unique = [(h, l) for h, l in zip(handles, labels_leg) if l not in seen and not seen.add(l)]
    ax1.legend(*zip(*unique), loc="upper right", fontsize=8)

    ax1.set_ylabel("Turbidez (NTU)")
    ax1.set_title(f"Turbidez vs. tiempo  —  zonas rojas = válvula rechazo activa", pad=6, fontsize=9)

    # --- Panel inferior: Estado de la válvula ---
    estado_valvula = label_vals.astype(float)
    ax2.fill_between(range(len(t)), estado_valvula,
                     step="post", alpha=0.7,
                     color=NASA["red"],   where=estado_valvula > 0, label="RECHAZO")
    ax2.fill_between(range(len(t)), 1 - estado_valvula,
                     step="post", alpha=0.5,
                     color=NASA["green"], where=estado_valvula == 0, label="ADMISIÓN")
    ax2.set_ylim(0, 1.3)
    ax2.set_yticks([0.5])
    ax2.set_yticklabels(["VÁLVULA"], fontsize=7)
    ax2.set_xlabel("Tiempo (muestras cada 30 min)")
    ax2.set_title("Estado de la válvula (FSM autónomo)", pad=4, fontsize=9)
    ax2.legend(loc="upper right", fontsize=8)

    fig.text(0.99, 0.01, "HYDRO-V MISSION CONTROL · SENSOR ANALYTICS",
             ha="right", va="bottom", fontsize=7,
             color=NASA["subtext"], alpha=0.6)

    plt.tight_layout()
    if save:
        path = FIGURES_DIR / "05_turbidity_timeline.png"
        fig.savefig(path, dpi=150, bbox_inches="tight",
                    facecolor=NASA["bg"])
        print(f"[Viz] Guardado: {path}")
    return fig


# ════════════════════════════════════════════════════════════
#  GRÁFICA 6 — PREDICCIÓN DE AUTONOMÍA POR COLONIA
# ════════════════════════════════════════════════════════════

def plot_autonomy_forecast(
    colonias: list[str],
    dias_restantes: list[float],
    niveles_pct: list[float],
    save: bool = True,
) -> plt.Figure:
    """
    Barras horizontales de días de autonomía estimados por colonia.
    Muestra el impacto social del sistema ante el jurado.

    Args:
        colonias       : Nombre de cada colonia.
        dias_restantes : Predicción de días de agua restante.
        niveles_pct    : Nivel actual de cisterna (0–100%).
        save           : Si True, guarda la imagen.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle(
        "HYDRO-V  ·  WATER AUTONOMY FORECAST  —  NEZA NETWORK",
        color=NASA["cyan"], fontsize=13, fontweight="bold",
        fontfamily="monospace",
    )

    idx = np.argsort(dias_restantes)
    col_sorted  = [colonias[i]      for i in idx]
    dias_sorted = [dias_restantes[i] for i in idx]
    niv_sorted  = [niveles_pct[i]   for i in idx]

    colores_barras = [
        NASA["red"]    if d < 2  else
        NASA["yellow"] if d < 4  else
        NASA["green"]
        for d in dias_sorted
    ]

    # --- Panel izquierdo: Días de autonomía ---
    bars = ax1.barh(col_sorted, dias_sorted, color=colores_barras,
                    alpha=0.8, height=0.6, edgecolor=NASA["grid"])

    for bar, dias in zip(bars, dias_sorted):
        ax1.text(bar.get_width() + 0.05, bar.get_y() + bar.get_height() / 2,
                 f"{dias:.1f} días", va="center", fontsize=8,
                 color=NASA["text"])

    ax1.axvline(2, color=NASA["red"],    lw=1.2, linestyle="--",
                alpha=0.7, label="Crítico (< 2 días)")
    ax1.axvline(4, color=NASA["yellow"], lw=1.2, linestyle="--",
                alpha=0.7, label="Alerta (< 4 días)")
    ax1.set_xlabel("Días de agua restante (predicción IA)")
    ax1.set_title("Autonomía estimada por colonia", pad=8)
    ax1.legend(fontsize=8)

    # --- Panel derecho: Nivel actual de cisterna ---
    colores_nivel = [
        NASA["red"]    if n < 20 else
        NASA["yellow"] if n < 50 else
        NASA["green"]
        for n in niv_sorted
    ]

    ax2.barh(col_sorted, niv_sorted, color=colores_nivel,
             alpha=0.8, height=0.6, edgecolor=NASA["grid"])

    for i, niv in enumerate(niv_sorted):
        ax2.text(niv + 0.5, i, f"{niv:.0f}%", va="center", fontsize=8,
                 color=NASA["text"])

    ax2.axvline(20, color=NASA["red"],    lw=1.2, linestyle="--", alpha=0.7)
    ax2.axvline(50, color=NASA["yellow"], lw=1.2, linestyle="--", alpha=0.7)
    ax2.set_xlim(0, 115)
    ax2.set_xlabel("Nivel actual de cisterna (%)")
    ax2.set_title("Nivel de cisterna por colonia", pad=8)

    fig.text(0.99, 0.01, "HYDRO-V MISSION CONTROL · PREDICTIVE ANALYTICS",
             ha="right", va="bottom", fontsize=7,
             color=NASA["subtext"], alpha=0.6)

    plt.tight_layout()
    if save:
        path = FIGURES_DIR / "06_autonomy_forecast.png"
        fig.savefig(path, dpi=150, bbox_inches="tight",
                    facecolor=NASA["bg"])
        print(f"[Viz] Guardado: {path}")
    return fig


# ════════════════════════════════════════════════════════════
#  DEMO — genera todas las gráficas con datos sintéticos
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 55)
    print("  Hydro-V · Generando visualizaciones para concurso")
    print("=" * 55)

    from src.data.synthetic_generator import (
        generar_red_completa,
        generar_datos_nodo,
        construir_grafo_instantaneo,
    )

    # ── Generar datos base ────────────────────────────────────
    print("\n[1/6] Generando datos sintéticos...")
    df_red = generar_red_completa(dias=60)

    # ── Gráfica 1: Curvas de entrenamiento (simuladas) ────────
    print("[2/6] Curvas de entrenamiento...")
    np.random.seed(42)
    n_ep = 120
    tl = np.exp(-np.linspace(0.3, 2.5, n_ep)) + np.random.normal(0, 0.015, n_ep)
    vl = np.exp(-np.linspace(0.2, 2.2, n_ep)) + np.random.normal(0, 0.020, n_ep)
    va = 1 - np.exp(-np.linspace(0.1, 2.0, n_ep)) + np.random.normal(0, 0.015, n_ep)
    va = np.clip(va, 0, 1)
    plot_training_curves(tl.tolist(), vl.tolist(), va.tolist())

    # ── Gráfica 2: Matriz de confusión (simulada) ─────────────
    print("[3/6] Matriz de confusión...")
    np.random.seed(7)
    n_test = 120
    y_true = np.random.binomial(1, 0.28, n_test)
    noise  = np.random.binomial(1, 0.08, n_test)
    y_pred = np.where(noise == 1, 1 - y_true, y_true)
    plot_confusion_matrix(y_true, y_pred)

    # ── Gráfica 3: Grafo de red hídrica ───────────────────────
    print("[4/6] Grafo de la red hídrica...")
    grafo = construir_grafo_instantaneo(df_red)
    probs = np.random.beta(0.8, 3.0, grafo.num_nodes)
    probs[5]  = 0.92   # Inyectar un nodo con fuga alta
    probs[18] = 0.85
    probs[33] = 0.78
    plot_network_graph(
        grafo.edge_index.numpy(),
        probs,
        grafo.y.numpy(),
    )

    # ── Gráfica 4: Distribución de turbidez ───────────────────
    print("[5/6] Distribución de turbidez...")
    plot_turbidity_distribution(df_red)

    # ── Gráfica 5: Timeline de turbidez ───────────────────────
    print("[6/6] Timeline turbidez + válvula...")
    df_nodo = generar_datos_nodo(node_id=2, dias=14, seed=2)
    plot_turbidity_timeline(df_nodo, device_id="HYDRO-V-002")

    # ── Gráfica 6 (BONUS): Autonomía por colonia ─────────────
    print("[BONUS] Predicción de autonomía por colonia...")
    colonias_neza = [
        "El Sol", "Juárez Pantitlán", "Benito Juárez",
        "Ciudad Lago", "Las Flores", "Reforma",
        "Evolución", "Metropolitana", "Nezahualcóyotl",
    ]
    np.random.seed(99)
    dias_pred  = np.random.uniform(0.8, 7.5, len(colonias_neza)).tolist()
    niveles    = np.random.uniform(10, 95, len(colonias_neza)).tolist()
    plot_autonomy_forecast(colonias_neza, dias_pred, niveles)

    print(f"\n✓ Todas las gráficas guardadas en: {FIGURES_DIR.resolve()}")
    print("=" * 55)