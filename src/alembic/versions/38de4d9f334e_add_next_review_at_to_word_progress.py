"""Add next_review_at to word_progress

Revision ID: 38de4d9f334e
Revises: 25f219fad108
Create Date: 2025-07-05 11:25:41.001487

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = '38de4d9f334e'
down_revision = '25f219fad108'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('word_progress', sa.Column('next_review_at', sa.DateTime(timezone=True), nullable=True))
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE word_progress
            SET next_review_at = DATETIME('now', '+1 day')
            WHERE next_review_at IS NULL
        """
        )
    )


def downgrade():
    op.drop_column('word_progress', 'next_review_at')
