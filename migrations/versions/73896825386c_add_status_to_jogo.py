"""add status to jogo

Revision ID: 73896825386c
Revises: d0bdcd598a7a
Create Date: 2026-07-15 22:23:07.827691

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '73896825386c'
down_revision = 'd0bdcd598a7a'
branch_labels = None
depends_on = None


def upgrade():
    # Adiciona coluna status na tabela jogo
    with op.batch_alter_table('jogo', schema=None) as batch_op:
        batch_op.add_column(sa.Column('status', sa.String(length=10), nullable=True))


def downgrade():
    with op.batch_alter_table('jogo', schema=None) as batch_op:
        batch_op.drop_column('status')