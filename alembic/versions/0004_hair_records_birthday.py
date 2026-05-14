"""hair records and customer birthday

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-14
"""
from alembic import op
import sqlalchemy as sa

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('customers', sa.Column('birthday', sa.Date, nullable=True))

    op.create_table(
        'hair_records',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('customer_id', sa.Integer, sa.ForeignKey('customers.id'), nullable=False),
        sa.Column('staff_id', sa.Integer, sa.ForeignKey('staff.id'), nullable=True),
        sa.Column('record_date', sa.Date, nullable=False),
        sa.Column('service_names', sa.Text, server_default=''),
        sa.Column('color_formula', sa.Text, server_default=''),
        sa.Column('hair_condition', sa.String(50), server_default=''),
        sa.Column('notes', sa.Text, server_default=''),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table('hair_records')
    op.drop_column('customers', 'birthday')
