"""add_is_verified_to_users

Revision ID: e414ceba3bbd
Revises: a284b3a1a9c9
Create Date: 2026-06-15 15:55:51.028388

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e414ceba3bbd'
down_revision: Union[str, Sequence[str], None] = 'a284b3a1a9c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="0"))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("is_verified")
