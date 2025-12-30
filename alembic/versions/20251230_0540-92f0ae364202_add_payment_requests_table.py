"""add_payment_requests_table

Revision ID: 92f0ae364202
Revises: f9c3e663a2a4
Create Date: 2025-12-30 05:40:11.119283

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '92f0ae364202'
down_revision: Union[str, Sequence[str], None] = 'f9c3e663a2a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Создаем таблицу payment_requests
    # Примечание: enum paymentrequeststatus должен существовать в БД
    op.create_table(
        'payment_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('amount', sa.String(), nullable=False),
        sa.Column('comment', sa.String(), nullable=False),
        sa.Column('invoice_file_id', sa.String(), nullable=True),
        sa.Column('status', sa.Enum('pending', 'scheduled_today', 'scheduled_date', 'paid', 'cancelled', name='paymentrequeststatus', create_type=False), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('processing_by_id', sa.Integer(), nullable=True),
        sa.Column('paid_by_id', sa.Integer(), nullable=True),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
        sa.Column('scheduled_date', sa.Date(), nullable=True),
        sa.Column('payment_proof_file_id', sa.String(), nullable=True),
        sa.Column('worker_message_id', sa.BigInteger(), nullable=True),
        sa.Column('billing_message_id', sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['processing_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['paid_by_id'], ['users.id'], ondelete='SET NULL'),
    )

    # Создаем индексы
    op.create_index(op.f('ix_payment_requests_created_by_id'), 'payment_requests', ['created_by_id'], unique=False)
    op.create_index(op.f('ix_payment_requests_status'), 'payment_requests', ['status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Удаляем индексы
    op.drop_index(op.f('ix_payment_requests_status'), table_name='payment_requests')
    op.drop_index(op.f('ix_payment_requests_created_by_id'), table_name='payment_requests')

    # Удаляем таблицу
    op.drop_table('payment_requests')

    # Примечание: enum paymentrequeststatus не удаляется для избежания проблем с другими таблицами
