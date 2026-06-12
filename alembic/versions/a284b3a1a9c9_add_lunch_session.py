"""add_lunch_session

Revision ID: a284b3a1a9c9
Revises: ced276a8a437
Create Date: 2026-06-12 09:36:06.933170

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'a284b3a1a9c9'
down_revision: Union[str, Sequence[str], None] = 'ced276a8a437'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. lunch_sessions tablosunu oluştur (kazanan FK sonra batch ile eklenecek)
    op.create_table(
        'lunch_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tarih', sa.Date(), nullable=False),
        sa.Column('durum', sa.Enum('aktif', 'kapandi', name='sessiondurum'), nullable=False),
        sa.Column('kazanan_mekan_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_lunch_sessions_id', 'lunch_sessions', ['id'], unique=False)
    op.create_index('ix_lunch_sessions_tarih', 'lunch_sessions', ['tarih'], unique=True)

    # 2. mekan_onerileri: session_id ekle (batch mode — SQLite uyumlu)
    with op.batch_alter_table('mekan_onerileri') as batch_op:
        batch_op.add_column(sa.Column('session_id', sa.Integer(), nullable=False, server_default='0'))
        batch_op.create_index('ix_mekan_onerileri_session_id', ['session_id'])
        batch_op.create_foreign_key('fk_mekan_session', 'lunch_sessions', ['session_id'], ['id'], ondelete='CASCADE')

    # 3. oylar: session_id ekle (batch mode — SQLite uyumlu)
    with op.batch_alter_table('oylar') as batch_op:
        batch_op.add_column(sa.Column('session_id', sa.Integer(), nullable=False, server_default='0'))
        batch_op.create_index('ix_oylar_session_id', ['session_id'])
        batch_op.create_foreign_key('fk_oy_session', 'lunch_sessions', ['session_id'], ['id'], ondelete='CASCADE')

    # 4. lunch_sessions.kazanan_mekan_id FK (batch mode)
    with op.batch_alter_table('lunch_sessions') as batch_op:
        batch_op.create_foreign_key('fk_session_kazanan', 'mekan_onerileri', ['kazanan_mekan_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    with op.batch_alter_table('lunch_sessions') as batch_op:
        batch_op.drop_constraint('fk_session_kazanan', type_='foreignkey')

    with op.batch_alter_table('oylar') as batch_op:
        batch_op.drop_constraint('fk_oy_session', type_='foreignkey')
        batch_op.drop_index('ix_oylar_session_id')
        batch_op.drop_column('session_id')

    with op.batch_alter_table('mekan_onerileri') as batch_op:
        batch_op.drop_constraint('fk_mekan_session', type_='foreignkey')
        batch_op.drop_index('ix_mekan_onerileri_session_id')
        batch_op.drop_column('session_id')

    op.drop_index('ix_lunch_sessions_tarih', table_name='lunch_sessions')
    op.drop_index('ix_lunch_sessions_id', table_name='lunch_sessions')
    op.drop_table('lunch_sessions')
    op.execute("DROP TYPE IF EXISTS sessiondurum")
