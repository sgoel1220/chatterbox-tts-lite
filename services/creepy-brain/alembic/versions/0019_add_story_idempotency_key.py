"""Add idempotency_key column to stories table.

Enables safe replay of POST /api/stories/ingest: a caller that supplies
the same idempotency_key receives the original story row instead of a
duplicate insert.

Revision ID: 0019
Revises: 0018
Create Date: 2026-04-25
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0019"
down_revision: str = "0018"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    op.add_column(
        "stories",
        sa.Column("idempotency_key", sa.String(128), nullable=True),
    )
    op.create_unique_constraint(
        "uq_stories_idempotency_key",
        "stories",
        ["idempotency_key"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_stories_idempotency_key", "stories", type_="unique")
    op.drop_column("stories", "idempotency_key")
