"""add_leak_detections_and_emergency_alerts

Revision ID: c3a1d9e7f204
Revises: f289bcd1edbc
Create Date: 2026-04-28 00:00:00.000000

Crea las tablas que los dashboards de Grafana y las reglas de alerting
necesitan pero que nunca fueron modeladas en la arquitectura v2.0:

  - leak_detections  → resultados del modelo GNN de detección de fugas
  - emergency_alerts → eventos EMERGENCY de la FSM del ESP32

Contexto:
  El modelo ORM Device ya tenía el relationship 'leak_detections' comentado.
  Esta migración lo hace efectivo. Los dashboards hydrov_network_intelligence
  y hydrov_mission_control apuntan a estas tablas con rawSql.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c3a1d9e7f204'
down_revision: Union[str, None] = 'f289bcd1edbc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── leak_detections ─────────────────────────────────────────────
    # Almacena los resultados de inferencia del modelo GNN GraphSAGE.
    # Cada fila representa una predicción de fuga para un nodo/timestamp.
    # Referenciada en:
    #   - hydrov_network_intelligence.json (paneles de inteligencia de red)
    #   - infra/grafana/provisioning/alerting/rules.yml (regla de alerta GNN)
    op.create_table(
        'leak_detections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column(
            'device_id',
            sa.Integer(),
            sa.ForeignKey('devices.id', name='fk_leak_detections_device_id_devices', ondelete='CASCADE'),
            nullable=False,
            index=True,
        ),
        # node_id como VARCHAR para queries directas de Grafana sin JOIN
        sa.Column('node_id', sa.String(length=50), nullable=False, index=True),
        sa.Column(
            'detected_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
            index=True,
        ),
        sa.Column(
            'anomaly_score',
            sa.Float(),
            sa.CheckConstraint('anomaly_score >= 0.0 AND anomaly_score <= 1.0', name='ck_leak_detections_score_range'),
            nullable=False,
        ),
        sa.Column('severity', sa.String(length=20), nullable=False, server_default='medium'),
        sa.Column('model_version', sa.String(length=20), nullable=True),
        sa.Column('neighbor_count', sa.Integer(), nullable=True),
        sa.Column(
            'payload_snapshot',
            postgresql.JSONB(astext_type=sa.Text()),
            server_default='{}',
            nullable=False,
        ),
        sa.Column('resolved', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name='pk_leak_detections'),
    )
    op.create_index('idx_leak_detections_active', 'leak_detections', ['node_id'], unique=False,
                    postgresql_where=sa.text('resolved = false'))
    op.create_index('idx_leak_detections_score', 'leak_detections', ['anomaly_score'], unique=False)

    # ── emergency_alerts ────────────────────────────────────────────
    # Registra los eventos SYSTEM_ERROR / EMERGENCY de la FSM del ESP32.
    # Referenciada en:
    #   - hydrov_mission_control.json (anotaciones y panel de historial)
    # NOTA: Los errores de alta severidad también van a tabla 'alerts'.
    # Esta tabla es un log especializado para métricas de la FSM (error_count,
    # state_duration_ms) que no encajan bien en el schema genérico de alerts.
    op.create_table(
        'emergency_alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column(
            'device_id',
            sa.Integer(),
            sa.ForeignKey('devices.id', name='fk_emergency_alerts_device_id_devices', ondelete='CASCADE'),
            nullable=False,
            index=True,
        ),
        # node_id como VARCHAR para queries directas de Grafana sin JOIN
        sa.Column('node_id', sa.String(length=50), nullable=False, index=True),
        sa.Column(
            'timestamp',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
            index=True,
        ),
        sa.Column('error_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('state_duration_ms', sa.BigInteger(), nullable=True),
        sa.Column('fsm_state', sa.String(length=30), nullable=True),
        sa.Column(
            'payload_snapshot',
            postgresql.JSONB(astext_type=sa.Text()),
            server_default='{}',
            nullable=False,
        ),
        sa.Column('resolved', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name='pk_emergency_alerts'),
    )
    op.create_index('idx_emergency_alerts_active', 'emergency_alerts', ['node_id'], unique=False,
                    postgresql_where=sa.text('resolved = false'))


def downgrade() -> None:
    op.drop_index('idx_emergency_alerts_active', table_name='emergency_alerts')
    op.drop_table('emergency_alerts')
    op.drop_index('idx_leak_detections_score', table_name='leak_detections')
    op.drop_index('idx_leak_detections_active', table_name='leak_detections')
    op.drop_table('leak_detections')
