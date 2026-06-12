"""Phase 5 premium features

Revision ID: 003
Revises: 002
Create Date: 2026-06-11

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("events", sa.Column("delivery_token", sa.String(64), nullable=True))
    op.add_column("events", sa.Column("delivery_enabled", sa.Boolean(), server_default="false"))
    op.create_index("ix_events_delivery_token", "events", ["delivery_token"], unique=True)

    op.add_column("audio_messages", sa.Column("starred", sa.Boolean(), server_default="false"))
    op.add_column("export_jobs", sa.Column("options_json", JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("export_jobs", "options_json")
    op.drop_column("audio_messages", "starred")
    op.drop_index("ix_events_delivery_token", table_name="events")
    op.drop_column("events", "delivery_enabled")
    op.drop_column("events", "delivery_token")
