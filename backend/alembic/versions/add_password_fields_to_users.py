"""Add password fields to users table

Revision ID: add_password_fields
Revises: dae1aa51750a
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_password_fields'
down_revision = 'dae1aa51750a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add password fields to users table
    op.add_column('users', sa.Column('password_hash', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    # Remove password fields from users table
    op.drop_column('users', 'email_verified')
    op.drop_column('users', 'is_active')
    op.drop_column('users', 'password_hash')