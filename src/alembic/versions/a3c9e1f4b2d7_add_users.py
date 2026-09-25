"""Add users and bind word progress to them

Revision ID: a3c9e1f4b2d7
Revises: 7b1f350c8821
Create Date: 2026-09-25 00:00:00.000000

"""

from os import getenv

import sqlalchemy as sa

from alembic import op

revision = 'a3c9e1f4b2d7'
down_revision = '7b1f350c8821'
branch_labels = None
depends_on = None

FK_NAME = 'fk_word_progress_user_id_users'
UQ_NAME = 'uq_word_progress_user_id_word_id'


def get_admin_telegram_id() -> int:
    admin_id = getenv('ADMIN_ID')
    if not admin_id:
        raise RuntimeError('ADMIN_ID environment variable is required to bind existing word progress to the admin.')
    return int(admin_id)


def create_users_table():
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('telegram_id', sa.BigInteger(), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('telegram_id', name='uq_users_telegram_id'),
    )


def bind_progress_to_admin(admin_telegram_id: int):
    conn = op.get_bind()
    params = {'telegram_id': admin_telegram_id}
    conn.execute(
        sa.text('INSERT INTO users (telegram_id, created_at) VALUES (:telegram_id, CURRENT_TIMESTAMP)'), params
    )
    conn.execute(
        sa.text('UPDATE word_progress SET user_id = (SELECT id FROM users WHERE telegram_id = :telegram_id)'), params
    )


def upgrade():
    admin_telegram_id = get_admin_telegram_id()
    create_users_table()
    with op.batch_alter_table('word_progress') as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
    bind_progress_to_admin(admin_telegram_id)
    with op.batch_alter_table('word_progress') as batch_op:
        batch_op.alter_column('user_id', existing_type=sa.Integer(), nullable=False)
        batch_op.create_foreign_key(FK_NAME, 'users', ['user_id'], ['id'], ondelete='CASCADE')
        batch_op.create_unique_constraint(UQ_NAME, ['user_id', 'word_id'])


def downgrade():
    with op.batch_alter_table('word_progress') as batch_op:
        batch_op.drop_constraint(UQ_NAME, type_='unique')
        batch_op.drop_constraint(FK_NAME, type_='foreignkey')
        batch_op.drop_column('user_id')
    op.drop_table('users')
