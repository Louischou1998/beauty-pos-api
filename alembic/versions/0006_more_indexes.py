"""add indexes for commissions and payments

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-14
"""
from alembic import op

revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index('ix_commissions_staff_id', 'commissions', ['staff_id'])
    op.create_index('ix_commissions_created_at', 'commissions', ['created_at'])
    op.create_index('ix_payments_created_at', 'payments', ['created_at'])
    op.create_index('ix_payments_booking_id', 'payments', ['booking_id'])


def downgrade():
    op.drop_index('ix_payments_booking_id', 'payments')
    op.drop_index('ix_payments_created_at', 'payments')
    op.drop_index('ix_commissions_created_at', 'commissions')
    op.drop_index('ix_commissions_staff_id', 'commissions')
