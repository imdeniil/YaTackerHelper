"""create_payment_request_status_enum

Revision ID: c5c18ce9d8cc
Revises: 4afc7c6a1fe1
Create Date: 2025-12-30 07:24:04.289657

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5c18ce9d8cc'
down_revision: Union[str, Sequence[str], None] = '4afc7c6a1fe1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Проверяем существует ли enum тип и пересоздаем его с правильными значениями
    # Также пересоздаем таблицу payment_requests если она существовала с неправильным enum
    op.execute("""
        DO $$
        BEGIN
            -- Проверяем существует ли enum
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'paymentrequeststatus') THEN
                -- Если существует таблица payment_requests - удаляем её
                DROP TABLE IF EXISTS payment_requests CASCADE;
                -- Удаляем старый enum
                DROP TYPE paymentrequeststatus;
            END IF;

            -- Создаем enum с правильными значениями (lowercase)
            CREATE TYPE paymentrequeststatus AS ENUM (
                'pending',
                'scheduled_today',
                'scheduled_date',
                'paid',
                'cancelled'
            );
        END $$;
    """)

    # Пересоздаем таблицу payment_requests с правильным enum типом
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
    # Не удаляем enum тип при downgrade, так как он может использоваться таблицей
    pass
