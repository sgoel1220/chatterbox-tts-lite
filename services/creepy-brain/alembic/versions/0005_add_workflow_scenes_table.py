"""Add workflow_scenes table and link chunks to scenes.

Separates image generation into its own table:
- workflow_scenes: one per N chunks, holds prompt and image blob
- workflow_chunks: now has scene_id FK, removed image fields

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-17
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0005"
down_revision: str = "0004"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    # Create workflow_scenes table
    op.create_table(
        "workflow_scenes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("workflow_id", UUID(as_uuid=True), sa.ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scene_index", sa.Integer(), nullable=False),
        sa.Column("image_prompt", sa.Text(), nullable=True),
        sa.Column("image_negative_prompt", sa.Text(), nullable=True),
        sa.Column("image_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("image_blob_id", UUID(as_uuid=True), nullable=True),
        sa.Column("image_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("workflow_id", "scene_index"),
    )
    op.create_index("idx_workflow_scenes_workflow", "workflow_scenes", ["workflow_id"])

    # Add scene_id to workflow_chunks
    op.add_column(
        "workflow_chunks",
        sa.Column("scene_id", UUID(as_uuid=True), sa.ForeignKey("workflow_scenes.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("idx_workflow_chunks_scene", "workflow_chunks", ["scene_id"])

    # Remove old image columns from workflow_chunks
    op.drop_column("workflow_chunks", "image_status")
    op.drop_column("workflow_chunks", "image_prompt")
    op.drop_column("workflow_chunks", "image_blob_id")
    op.drop_column("workflow_chunks", "image_completed_at")


def downgrade() -> None:
    # Add back image columns to workflow_chunks
    op.add_column("workflow_chunks", sa.Column("image_completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("workflow_chunks", sa.Column("image_blob_id", UUID(as_uuid=True), nullable=True))
    op.add_column("workflow_chunks", sa.Column("image_prompt", sa.Text(), nullable=True))
    op.add_column("workflow_chunks", sa.Column("image_status", sa.String(20), nullable=False, server_default="pending"))

    # Remove scene_id from workflow_chunks
    op.drop_index("idx_workflow_chunks_scene", table_name="workflow_chunks")
    op.drop_column("workflow_chunks", "scene_id")

    # Drop workflow_scenes table
    op.drop_index("idx_workflow_scenes_workflow", table_name="workflow_scenes")
    op.drop_table("workflow_scenes")
