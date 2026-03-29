"""Add ML prediction tables: autonomy_predictions and leak_detections

Revision ID: 0002_ml_tables
Revises: 0001_initial_schema
Create Date: 2026-03-28

Tablas creadas:
  - autonomy_predictions  → resultados del modelo LinearRegression (días de agua)
  - leak_detections       → resultados del modelo GNN/MLP (detección de fugas)

Estas tablas alimentan:
  - Panel 12 "Predicción IA" del dashboard Mission Control
  - Dashboard completo Network Intelligence (GNN)
  - Endpoint GET /api/v1/predictions/{node_id}/autonomy (guarda resultado)
  - Endpoint GET /api/v1/predictions/{node_id}/leaks (guarda resultado)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0002_ml_tables"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


# ─────────────────────────────────────────────────────────────────
#  UPGRADE
# ─────────────────────────────────────────────────────────────────

def upgrade() -> None:

    # ── autonomy_predictions ─────────────────────────────────────
    # Registra cada predicción de días de autonomía hídrica.
    # El scheduler de APScheduler escribe aquí cada hora.
    # También lo escribe el endpoint /predictions/{node_id}/autonomy.
    op.create_table(
        "autonomy_predictions",
        sa.Column("id",              sa.Integer(),     nullable=False),
        sa.Column("node_id",         sa.String(50),    nullable=False),
        sa.Column("created_at",      sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        # Features usadas en la predicción (para auditoría y reentrenamiento)
        sa.Column("level_pct",           sa.Float(), nullable=False),
        sa.Column("avg_consumption_lpd", sa.Float(), nullable=False),
        sa.Column("forecast_precip_mm",  sa.Float(), nullable=False),
        sa.Column("temperature_c",       sa.Float(), nullable=False),
        sa.Column("humidity_pct",        sa.Float(), nullable=False),
        sa.Column("days_without_rain",   sa.Integer(), nullable=False),
        sa.Column("month",               sa.Integer(), nullable=False),
        # Resultado del modelo
        sa.Column("days_autonomy",   sa.Float(),   nullable=False),
        sa.Column("confidence",      sa.Float(),   nullable=False, server_default=sa.text("0.85")),
        sa.Column("alert",           sa.Boolean(), nullable=False, server_default=sa.text("false")),
        # Metadata del modelo usado
        sa.Column("model_version",   sa.String(50), nullable=False, server_default=sa.text("'v1-baseline'")),
        sa.ForeignKeyConstraint(
            ["node_id"], ["devices.device_id"],
            name=op.f("fk_autonomy_predictions_node_id_devices"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_autonomy_predictions")),
    )
    op.create_index(op.f("ix_autonomy_predictions_id"),         "autonomy_predictions", ["id"],         unique=False)
    op.create_index(op.f("ix_autonomy_predictions_node_id"),    "autonomy_predictions", ["node_id"],    unique=False)
    op.create_index(op.f("ix_autonomy_predictions_created_at"), "autonomy_predictions", ["created_at"], unique=False)

    # ── leak_detections ──────────────────────────────────────────
    # Registra cada detección del modelo GNN/MLP de anomalías de flujo.
    # Se persiste cuando anomaly_score >= 0.75 (umbral de fuga probable).
    op.create_table(
        "leak_detections",
        sa.Column("id",             sa.Integer(),  nullable=False),
        sa.Column("node_id",        sa.String(50), nullable=False),
        sa.Column("detected_at",    sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        # Features usadas por el modelo
        sa.Column("flow_lpm",       sa.Float(), nullable=False),
        sa.Column("level_pct",      sa.Float(), nullable=False),
        # Resultado del modelo
        sa.Column("anomaly_score",  sa.Float(), nullable=False),
        sa.Column("leak_detected",  sa.Boolean(), nullable=False),
        sa.Column("confidence",     sa.Float(), nullable=False, server_default=sa.text("0.80")),
        # Features de nodos vecinos (JSON — vacío si es nodo único)
        sa.Column("neighbor_data",  JSONB(), nullable=False, server_default=sa.text("'[]'")),
        # Resolución manual (el operador puede marcarlo como falso positivo)
        sa.Column("resolved",       sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("resolved_notes", sa.Text(),    nullable=True),
        sa.Column("resolved_at",    sa.DateTime(timezone=True), nullable=True),
        # Metadata del modelo
        sa.Column("model_version",  sa.String(50), nullable=False, server_default=sa.text("'v1-mlp-baseline'")),
        sa.ForeignKeyConstraint(
            ["node_id"], ["devices.device_id"],
            name=op.f("fk_leak_detections_node_id_devices"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_leak_detections")),
    )
    op.create_index(op.f("ix_leak_detections_id"),          "leak_detections", ["id"],          unique=False)
    op.create_index(op.f("ix_leak_detections_node_id"),     "leak_detections", ["node_id"],     unique=False)
    op.create_index(op.f("ix_leak_detections_detected_at"), "leak_detections", ["detected_at"], unique=False)
    # Índice parcial: solo fugas detectadas (no falsas alarmas) — útil para queries del dashboard
    op.execute(
        "CREATE INDEX ix_leak_detections_active ON leak_detections (node_id, detected_at) "
        "WHERE leak_detected = true AND resolved = false"
    )


# ─────────────────────────────────────────────────────────────────
#  DOWNGRADE
# ─────────────────────────────────────────────────────────────────

def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_leak_detections_active")

    op.drop_index(op.f("ix_leak_detections_detected_at"), table_name="leak_detections")
    op.drop_index(op.f("ix_leak_detections_node_id"),     table_name="leak_detections")
    op.drop_index(op.f("ix_leak_detections_id"),          table_name="leak_detections")
    op.drop_table("leak_detections")

    op.drop_index(op.f("ix_autonomy_predictions_created_at"), table_name="autonomy_predictions")
    op.drop_index(op.f("ix_autonomy_predictions_node_id"),    table_name="autonomy_predictions")
    op.drop_index(op.f("ix_autonomy_predictions_id"),         table_name="autonomy_predictions")
    op.drop_table("autonomy_predictions")
