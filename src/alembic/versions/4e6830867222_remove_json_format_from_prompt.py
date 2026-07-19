"""Remove JSON format from translate prompt

Revision ID: 4e6830867222
Revises: 38de4d9f334e
Create Date: 2026-07-19 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = '4e6830867222'
down_revision = '38de4d9f334e'
branch_labels = None
depends_on = None

LEGACY_JSON_FORMAT_MARKER = 'Ответ пришли в фомите JSON:'


def upgrade():
    connection = op.get_bind()
    prompts = connection.execute(
        sa.text('SELECT id, text FROM prompts WHERE name = :name'),
        {'name': 'translate'},
    ).mappings()
    for prompt in prompts:
        text = prompt['text']
        if text and LEGACY_JSON_FORMAT_MARKER in text:
            clean_text = text.split(LEGACY_JSON_FORMAT_MARKER, maxsplit=1)[0].rstrip()
            connection.execute(
                sa.text('UPDATE prompts SET text = :text WHERE id = :id'),
                {'id': prompt['id'], 'text': clean_text},
            )


def downgrade():
    pass
