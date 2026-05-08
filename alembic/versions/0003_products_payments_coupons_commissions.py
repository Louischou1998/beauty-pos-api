"""products payments coupons commissions

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-07
"""
from alembic import op
import sqlalchemy as sa

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'products',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('category', sa.String(50)),
        sa.Column('price', sa.Numeric(10, 2), nullable=False),
        sa.Column('cost', sa.Numeric(10, 2), server_default='0'),
        sa.Column('stock', sa.Integer, server_default='0'),
        sa.Column('barcode', sa.String(50)),
        sa.Column('is_active', sa.Integer, server_default='1'),
    )

    op.create_table(
        'payments',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('booking_id', sa.Integer, sa.ForeignKey('bookings.id'), nullable=False),
        sa.Column('method', sa.String(20), nullable=False),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('note', sa.String(200)),
    )

    op.create_table(
        'coupons',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('code', sa.String(50), unique=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('type', sa.String(20), nullable=False),
        sa.Column('value', sa.Numeric(10, 2), nullable=False),
        sa.Column('min_amount', sa.Numeric(10, 2), server_default='0'),
        sa.Column('max_uses', sa.Integer, server_default='0'),
        sa.Column('used_count', sa.Integer, server_default='0'),
        sa.Column('valid_from', sa.DateTime),
        sa.Column('valid_until', sa.DateTime),
        sa.Column('is_active', sa.Integer, server_default='1'),
    )

    op.create_table(
        'coupon_usages',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('coupon_id', sa.Integer, nullable=False),
        sa.Column('booking_id', sa.Integer, nullable=False),
        sa.Column('customer_id', sa.Integer),
        sa.Column('discount_amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('used_at', sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        'commissions',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('booking_id', sa.Integer, sa.ForeignKey('bookings.id'), nullable=False),
        sa.Column('staff_id', sa.Integer, sa.ForeignKey('staff.id'), nullable=False),
        sa.Column('type', sa.String(20), nullable=False),
        sa.Column('item_name', sa.String(100)),
        sa.Column('is_designated', sa.Boolean, server_default='false'),
        sa.Column('base_amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('commission_rate', sa.Numeric(5, 2), nullable=False),
        sa.Column('commission_amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    # 顧客 CRM 欄位擴充
    op.add_column('customers', sa.Column('allergy_info', sa.Text, server_default=''))
    op.add_column('customers', sa.Column('preferred_staff_id', sa.Integer, sa.ForeignKey('staff.id'), nullable=True))
    op.add_column('customers', sa.Column('revisit_days', sa.Integer, server_default='30'))
    op.add_column('customers', sa.Column('last_visit_at', sa.DateTime, nullable=True))


def downgrade():
    op.drop_column('customers', 'last_visit_at')
    op.drop_column('customers', 'revisit_days')
    op.drop_column('customers', 'preferred_staff_id')
    op.drop_column('customers', 'allergy_info')
    op.drop_table('commissions')
    op.drop_table('coupon_usages')
    op.drop_table('coupons')
    op.drop_table('payments')
    op.drop_table('products')
