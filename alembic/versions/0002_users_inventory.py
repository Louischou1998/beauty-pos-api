"""users and inventory tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-07
"""
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('email', sa.String(100), unique=True, nullable=False),
        sa.Column('hashed_password', sa.String(200), nullable=False),
        sa.Column('role', sa.String(20), server_default='staff'),
        sa.Column('staff_id', sa.Integer, sa.ForeignKey('staff.id'), nullable=True),
        sa.Column('is_active', sa.Integer, server_default='1'),
    )

    op.create_table(
        'inventory_items',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('category', sa.String(50)),
        sa.Column('unit', sa.String(20), server_default='個'),
        sa.Column('quantity', sa.Numeric(10, 2), server_default='0'),
        sa.Column('low_stock_threshold', sa.Numeric(10, 2), server_default='10'),
        sa.Column('cost_per_unit', sa.Numeric(10, 2), server_default='0'),
    )

    op.create_table(
        'inventory_usage',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('item_id', sa.Integer, sa.ForeignKey('inventory_items.id'), nullable=False),
        sa.Column('booking_id', sa.Integer, sa.ForeignKey('bookings.id'), nullable=True),
        sa.Column('staff_id', sa.Integer, sa.ForeignKey('staff.id'), nullable=True),
        sa.Column('quantity_used', sa.Numeric(10, 2), nullable=False),
        sa.Column('used_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('note', sa.String(200)),
    )


def downgrade():
    op.drop_table('inventory_usage')
    op.drop_table('inventory_items')
    op.drop_table('users')
