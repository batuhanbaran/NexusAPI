"""initial_schema

Revision ID: ced276a8a437
Revises:
Create Date: 2026-06-11 16:17:21.955313

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'ced276a8a437'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('isim', sa.String(length=100), nullable=False),
        sa.Column('soyisim', sa.String(length=100), nullable=False),
        sa.Column('mail', sa.String(length=255), nullable=False),
        sa.Column('cinsiyet', sa.Enum('erkek', 'kadin', 'diger', name='cinsiyet'), nullable=False),
        sa.Column('sifre_hash', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_id', 'users', ['id'], unique=False)
    op.create_index('ix_users_mail', 'users', ['mail'], unique=True)

    op.create_table(
        'mekan_onerileri',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('isim', sa.String(length=200), nullable=False),
        sa.Column('adres', sa.String(length=500), nullable=False),
        sa.Column('mutfak_turu', sa.String(length=100), nullable=False),
        sa.Column('onerilen_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['onerilen_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_mekan_onerileri_id', 'mekan_onerileri', ['id'], unique=False)

    op.create_table(
        'oylar',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('kullanici_id', sa.Integer(), nullable=False),
        sa.Column('mekan_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['kullanici_id'], ['users.id']),
        sa.ForeignKeyConstraint(['mekan_id'], ['mekan_onerileri.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('kullanici_id', 'mekan_id', name='uq_kullanici_mekan_oyu'),
    )
    op.create_index('ix_oylar_id', 'oylar', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_oylar_id', table_name='oylar')
    op.drop_table('oylar')
    op.drop_index('ix_mekan_onerileri_id', table_name='mekan_onerileri')
    op.drop_table('mekan_onerileri')
    op.drop_index('ix_users_mail', table_name='users')
    op.drop_index('ix_users_id', table_name='users')
    op.drop_table('users')
    op.execute("DROP TYPE IF EXISTS cinsiyet")
