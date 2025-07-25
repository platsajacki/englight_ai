"""add word_progress table

Revision ID: 25f219fad108
Revises: 095767fcb6bd
Create Date: 2025-06-09 21:54:11.099033

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '25f219fad108'
down_revision: Union[str, None] = '095767fcb6bd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        'word_progress',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('word_id', sa.Integer(), nullable=False),
        sa.Column('review_history', sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(['word_id'], ['words.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('word_progress')
    # ### end Alembic commands ###
