"""add_document_comparison_table

Revision ID: 0f417e0e7d90
Revises: add_password_fields
Create Date: 2025-10-25 21:11:46.674454

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0f417e0e7d90'
down_revision: Union[str, None] = 'add_password_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create document_comparisons table
    op.create_table(
        'document_comparisons',
        sa.Column('id', sa.UUID(), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('org_id', sa.UUID(), nullable=False),
        sa.Column('document_a_id', sa.UUID(), nullable=False),
        sa.Column('document_b_id', sa.UUID(), nullable=False),
        sa.Column('comparison_result', postgresql.JSONB(), nullable=True),
        sa.Column('risk_assessment', postgresql.JSONB(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['org_id'], ['orgs.id']),
        sa.ForeignKeyConstraint(['document_a_id'], ['documents.id']),
        sa.ForeignKeyConstraint(['document_b_id'], ['documents.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for performance
    op.create_index('idx_document_comparisons_org_id', 'document_comparisons', ['org_id'])
    op.create_index('idx_document_comparisons_document_a', 'document_comparisons', ['document_a_id'])
    op.create_index('idx_document_comparisons_document_b', 'document_comparisons', ['document_b_id'])
    op.create_index('idx_document_comparisons_created_at', 'document_comparisons', ['created_at'])
    
    # Enable RLS for multi-tenancy
    op.execute('ALTER TABLE document_comparisons ENABLE ROW LEVEL SECURITY')
    
    # Create RLS policy
    op.execute('''
        CREATE POLICY document_comparisons_org_rls ON document_comparisons 
        USING (org_id::text = current_setting('app.current_org', true))
    ''')


def downgrade() -> None:
    # Drop RLS policy
    op.execute('DROP POLICY IF EXISTS document_comparisons_org_rls ON document_comparisons')
    
    # Drop indexes
    op.drop_index('idx_document_comparisons_created_at', 'document_comparisons')
    op.drop_index('idx_document_comparisons_document_b', 'document_comparisons')
    op.drop_index('idx_document_comparisons_document_a', 'document_comparisons')
    op.drop_index('idx_document_comparisons_org_id', 'document_comparisons')
    
    # Drop table
    op.drop_table('document_comparisons')
