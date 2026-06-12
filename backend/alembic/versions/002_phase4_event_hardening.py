"""Phase 4 event hardening

Revision ID: 002
Revises: 001
Create Date: 2026-06-11

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("events", sa.Column("retention_days", sa.Integer(), server_default="90"))
    op.add_column("audio_messages", sa.Column("snapshot_path", sa.Text(), nullable=True))
    op.add_column("devices", sa.Column("last_error_code", sa.String(50), nullable=True))
    op.add_column("devices", sa.Column("last_error_message", sa.Text(), nullable=True))
    op.add_column("devices", sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("devices", "last_error_at")
    op.drop_column("devices", "last_error_message")
    op.drop_column("devices", "last_error_code")
    op.drop_column("audio_messages", "snapshot_path")
    op.drop_column("events", "retention_days")
