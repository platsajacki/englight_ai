"""Make word and part of speech unique

Revision ID: 7b1f350c8821
Revises: 4e6830867222
Create Date: 2026-07-19 00:00:00.000000

"""

from alembic import op

revision = '7b1f350c8821'
down_revision = '4e6830867222'
branch_labels = None
depends_on = None

NAMING_CONVENTION = {'uq': 'uq_%(table_name)s_%(column_0_name)s'}


def upgrade():
    with op.batch_alter_table('words', naming_convention=NAMING_CONVENTION) as batch_op:
        batch_op.drop_constraint('uq_words_word', type_='unique')
        batch_op.create_unique_constraint('uq_words_word_part_of_speech', ['word', 'part_of_speech'])


def downgrade():
    with op.batch_alter_table('words', naming_convention=NAMING_CONVENTION) as batch_op:
        batch_op.drop_constraint('uq_words_word_part_of_speech', type_='unique')
        batch_op.create_unique_constraint('uq_words_word', ['word'])
