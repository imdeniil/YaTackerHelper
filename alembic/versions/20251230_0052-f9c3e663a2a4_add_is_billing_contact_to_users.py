"""add_is_billing_contact_to_users

Revision ID: f9c3e663a2a4
Revises: 
Create Date: 2025-12-30 00:52:10.466984

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f9c3e663a2a4'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Добавляем колонку is_billing_contact в таблицу users
    op.add_column('users', sa.Column('is_billing_contact', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    """Downgrade schema."""
    # Удаляем колонку is_billing_contact из таблицы users
    op.drop_column('users', 'is_billing_contact')
