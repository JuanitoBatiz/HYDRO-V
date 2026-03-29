"""initial schema — users, devices, telemetry_events, emergency_alerts

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-03-28

Tablas creadas:
  - users
  - devices
  - telemetry_events
  - emergency_alerts
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# ── Identificadores de revisión ───────────────────────────────────
revision = "0001_initial_schema"
down_revision = None         # Primera migración — sin predecesor
branch_labels = None
depends_on = None


# ─────────────────────────────────────────────────────────────────
#  UPGRADE — aplicar cambios
# ─────────────────────────────────────────────────────────────────

def upgrade() -> None:

    # ── users ─────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id",              sa.Integer(),     nullable=False),
        sa.Column("email",           sa.String(255),   nullable=False),
        sa.Column("name",            sa.String(100),   nullable=False),
        sa.Column("hashed_password", sa.String(255),   nullable=False),
        sa.Column("is_active",       sa.Boolean(),     nullable=False, server_default=sa.text("true")),
        sa.Column("is_superuser",    sa.Boolean(),     nullable=False, server_default=sa.text("false")),
        sa.Column("created_at",      sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at",      sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_id"),    "users", ["id"],    unique=False)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # ── devices ───────────────────────────────────────────────────
    op.create_table(
        "devices",
        sa.Column("id",           sa.Integer(),  nullable=False),
        sa.Column("device_id",    sa.String(50), nullable=False),
        sa.Column("name",         sa.String(100), nullable=False),
        sa.Column("lat",          sa.Float(),    nullable=False),
        sa.Column("lon",          sa.Float(),    nullable=False),
        sa.Column("location",     sa.String(200), nullable=True),
        sa.Column("roof_area_m2", sa.Float(),    nullable=False),
        sa.Column("is_active",    sa.Boolean(),  nullable=False, server_default=sa.text("true")),
        sa.Column("last_seen",    sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at",   sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_devices")),
        sa.UniqueConstraint("device_id", name=op.f("uq_devices_device_id")),
    )
    op.create_index(op.f("ix_devices_id"),        "devices", ["id"],        unique=False)
    op.create_index(op.f("ix_devices_device_id"), "devices", ["device_id"], unique=True)

    # ── telemetry_events ──────────────────────────────────────────
    op.create_table(
        "telemetry_events",
        sa.Column("id",                sa.Integer(),  nullable=False),
        sa.Column("device_id",         sa.String(50), nullable=False),
        sa.Column("received_at",       sa.DateTime(timezone=True), nullable=False),
        # Sensores
        sa.Column("turbidity_ntu",     sa.Float(),   nullable=False),
        sa.Column("distance_cm",       sa.Float(),   nullable=False),
        sa.Column("flow_lpm",          sa.Float(),   nullable=False),
        sa.Column("flow_total_liters", sa.Float(),   nullable=False),
        # Estado FSM
        sa.Column("state",             sa.String(20), nullable=False),
        sa.Column("state_duration_ms", sa.Integer(),  nullable=False),
        sa.Column("intake_cycles",     sa.Integer(),  nullable=False),
        sa.Column("reject_cycles",     sa.Integer(),  nullable=False),
        sa.Column("error_count",       sa.Integer(),  nullable=False),
        # Metadata
        sa.Column("esp32_uptime_ms",   sa.Integer(),  nullable=False),
        sa.Column("created_at",        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["device_id"], ["devices.device_id"],
            name=op.f("fk_telemetry_events_device_id_devices"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_telemetry_events")),
    )
    op.create_index(op.f("ix_telemetry_events_id"),          "telemetry_events", ["id"],          unique=False)
    op.create_index(op.f("ix_telemetry_events_device_id"),   "telemetry_events", ["device_id"],   unique=False)
    op.create_index(op.f("ix_telemetry_events_received_at"), "telemetry_events", ["received_at"], unique=False)

    # ── emergency_alerts ──────────────────────────────────────────
    op.create_table(
        "emergency_alerts",
        sa.Column("id",                sa.Integer(),  nullable=False),
        sa.Column("node_id",           sa.String(50), nullable=False),
        sa.Column("timestamp",         sa.DateTime(timezone=True), nullable=False),
        sa.Column("error_count",       sa.Integer(),  nullable=False),
        sa.Column("state_duration_ms", sa.Integer(),  nullable=False),
        sa.Column("payload_snapshot",  JSONB(),       nullable=False),
        sa.Column("resolved",          sa.Boolean(),  nullable=False, server_default=sa.text("false")),
        sa.Column("resolved_notes",    sa.Text(),     nullable=True),
        sa.Column("resolved_at",       sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at",        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["node_id"], ["devices.device_id"],
            name=op.f("fk_emergency_alerts_node_id_devices"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_emergency_alerts")),
    )
    op.create_index(op.f("ix_emergency_alerts_id"),        "emergency_alerts", ["id"],        unique=False)
    op.create_index(op.f("ix_emergency_alerts_node_id"),   "emergency_alerts", ["node_id"],   unique=False)
    op.create_index(op.f("ix_emergency_alerts_timestamp"), "emergency_alerts", ["timestamp"], unique=False)


# ─────────────────────────────────────────────────────────────────
#  DOWNGRADE — revertir (en orden inverso de creación)
# ─────────────────────────────────────────────────────────────────

def downgrade() -> None:
    # emergency_alerts primero (FK a devices)
    op.drop_index(op.f("ix_emergency_alerts_timestamp"), table_name="emergency_alerts")
    op.drop_index(op.f("ix_emergency_alerts_node_id"),   table_name="emergency_alerts")
    op.drop_index(op.f("ix_emergency_alerts_id"),        table_name="emergency_alerts")
    op.drop_table("emergency_alerts")

    # telemetry_events (FK a devices)
    op.drop_index(op.f("ix_telemetry_events_received_at"), table_name="telemetry_events")
    op.drop_index(op.f("ix_telemetry_events_device_id"),   table_name="telemetry_events")
    op.drop_index(op.f("ix_telemetry_events_id"),          table_name="telemetry_events")
    op.drop_table("telemetry_events")

    # devices
    op.drop_index(op.f("ix_devices_device_id"), table_name="devices")
    op.drop_index(op.f("ix_devices_id"),        table_name="devices")
    op.drop_table("devices")

    # users (sin FK — va al final)
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_index(op.f("ix_users_id"),    table_name="users")
    op.drop_table("users")
