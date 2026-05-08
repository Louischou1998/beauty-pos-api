"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'staff',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('phone', sa.String(20)),
        sa.Column('color', sa.String(10), server_default='#1677ff'),
        sa.Column('skills', postgresql.ARRAY(sa.String), server_default='{}'),
        sa.Column('commission_rate', sa.Numeric(5, 2), server_default='35'),
        sa.Column('is_active', sa.Integer, server_default='1'),
    )

    op.create_table(
        'service_categories',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(50), nullable=False),
    )

    op.create_table(
        'services',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('category_id', sa.Integer, sa.ForeignKey('service_categories.id')),
        sa.Column('duration', sa.Integer, nullable=False),
        sa.Column('price', sa.Numeric(10, 2), nullable=False),
        sa.Column('is_active', sa.Integer, server_default='1'),
    )

    op.create_table(
        'customers',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('phone', sa.String(20), unique=True),
        sa.Column('email', sa.String(100)),
        sa.Column('level', sa.String(20), server_default='一般'),
        sa.Column('points', sa.Integer, server_default='0'),
        sa.Column('balance', sa.Numeric(10, 2), server_default='0'),
        sa.Column('total_spent', sa.Numeric(10, 2), server_default='0'),
        sa.Column('visits', sa.Integer, server_default='0'),
    )

    op.create_table(
        'bookings',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('customer_id', sa.Integer, sa.ForeignKey('customers.id'), nullable=False),
        sa.Column('status', sa.String(20), server_default='pending'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('note', sa.String(500)),
    )

    op.create_table(
        'booking_items',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('booking_id', sa.Integer, sa.ForeignKey('bookings.id'), nullable=False),
        sa.Column('service_id', sa.Integer, sa.ForeignKey('services.id'), nullable=False),
        sa.Column('staff_id', sa.Integer, sa.ForeignKey('staff.id'), nullable=False),
        sa.Column('start_at', sa.DateTime, nullable=False),
        sa.Column('end_at', sa.DateTime, nullable=False),
        sa.Column('price', sa.Numeric(10, 2), nullable=False),
    )

    op.create_index('ix_booking_items_staff_time', 'booking_items', ['staff_id', 'start_at', 'end_at'])


def downgrade():
    op.drop_table('booking_items')
    op.drop_table('bookings')
    op.drop_table('customers')
    op.drop_table('services')
    op.drop_table('service_categories')
    op.drop_table('staff')
