"""add missing indexes for query performance

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-14
"""
from alembic import op

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index('ix_bookings_customer_id', 'bookings', ['customer_id'])
    op.create_index('ix_bookings_status', 'bookings', ['status'])
    op.create_index('ix_booking_items_booking_id', 'booking_items', ['booking_id'])
    op.create_index('ix_booking_items_service_id', 'booking_items', ['service_id'])
    op.create_index('ix_hair_records_customer_id', 'hair_records', ['customer_id'])
    op.create_index('ix_customers_last_visit_at', 'customers', ['last_visit_at'])


def downgrade():
    op.drop_index('ix_customers_last_visit_at', 'customers')
    op.drop_index('ix_hair_records_customer_id', 'hair_records')
    op.drop_index('ix_booking_items_service_id', 'booking_items')
    op.drop_index('ix_booking_items_booking_id', 'booking_items')
    op.drop_index('ix_bookings_status', 'bookings')
    op.drop_index('ix_bookings_customer_id', 'bookings')
