"""force_fix_check_constraints

Revision ID: f289bcd1edbc
Revises: f199fab1addb
Create Date: 2026-04-06 22:42:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f289bcd1edbc'
down_revision: Union[str, None] = 'f199fab1addb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Zones constraints
    op.create_check_constraint('chk_zone_b04225', 'zones', 'latitude >= -90 AND latitude <= 90')
    op.create_check_constraint('chk_zone_f06d62', 'zones', 'longitude >= -180 AND longitude <= 180')

    # Devices constraints
    op.create_check_constraint('chk_device_069243', 'devices', "status IN ('active', 'inactive', 'maintenance')")

    # Valves constraints 
    op.create_check_constraint('chk_valve_177a0a', 'valves', "current_state IN ('open', 'closed')")

    # Alerts constraints
    op.create_check_constraint('chk_alert_f98914', 'alerts', "severity IN ('low', 'medium', 'high', 'critical')")
    op.create_check_constraint('chk_alert_85448e', 'alerts', 'confidence_score >= 0.0 AND confidence_score <= 1.0')


def downgrade() -> None:
    # Alerts constraints
    op.drop_constraint('chk_alert_85448e', 'alerts', type_='check')
    op.drop_constraint('chk_alert_f98914', 'alerts', type_='check')

    # Valves constraints
    op.drop_constraint('chk_valve_177a0a', 'valves', type_='check')

    # Devices constraints
    op.drop_constraint('chk_device_069243', 'devices', type_='check')

    # Zones constraints
    op.drop_constraint('chk_zone_f06d62', 'zones', type_='check')
    op.drop_constraint('chk_zone_b04225', 'zones', type_='check')
