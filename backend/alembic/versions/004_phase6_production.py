"""Phase 6 production polish

Revision ID: 004
Revises: 003
Create Date: 2026-06-11

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("events", sa.Column("booth_qr_enabled", sa.Boolean(), server_default="true"))


def downgrade() -> None:
    op.drop_column("events", "booth_qr_enabled")
