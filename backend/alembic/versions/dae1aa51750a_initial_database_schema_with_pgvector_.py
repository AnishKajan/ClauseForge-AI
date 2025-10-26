"""Initial database schema with pgvector and RLS

Revision ID: dae1aa51750a
Revises: 
Create Date: 2025-10-25 20:15:23.432755

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = 'dae1aa51750a'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable required extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    
    # Create organizations table
    op.create_table('orgs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('sso_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=True, server_default='viewer'),
        sa.Column('provider', sa.String(length=50), nullable=True, server_default='email'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['org_id'], ['orgs.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    
    # Create subscriptions table
    op.create_table('subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('stripe_customer_id', sa.String(length=255), nullable=True),
        sa.Column('plan', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=True, server_default='active'),
        sa.Column('usage_limits', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['org_id'], ['orgs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create documents table
    op.create_table('documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('s3_key', sa.String(length=500), nullable=False),
        sa.Column('file_type', sa.String(length=50), nullable=True),
        sa.Column('file_size', sa.BigInteger(), nullable=True),
        sa.Column('file_hash', sa.String(length=64), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True, server_default='uploaded'),
        sa.Column('uploaded_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['org_id'], ['orgs.id'], ),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create playbooks table
    op.create_table('playbooks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('rules_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['org_id'], ['orgs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create usage_records table
    op.create_table('usage_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('usage_type', sa.String(length=50), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=True),
        sa.Column('period_end', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['org_id'], ['orgs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create audits table
    op.create_table('audits',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=True),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('payload_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['org_id'], ['orgs.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create analyses table
    op.create_table('analyses',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('playbook_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('risk_score', sa.Integer(), nullable=True),
        sa.Column('summary_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('recommendations', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create clauses table
    op.create_table('clauses',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('clause_type', sa.String(length=100), nullable=True),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('confidence', sa.DECIMAL(precision=5, scale=4), nullable=True),
        sa.Column('page', sa.Integer(), nullable=True),
        sa.Column('risk_level', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create document_chunks table with vector embeddings
    op.create_table('document_chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('chunk_no', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(1536), nullable=True),
        sa.Column('page', sa.Integer(), nullable=True),
        sa.Column('chunk_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for performance
    op.create_index('idx_users_org_id', 'users', ['org_id'], unique=False)
    op.create_index('idx_subscriptions_org_id', 'subscriptions', ['org_id'], unique=False)
    op.create_index('idx_documents_org_id', 'documents', ['org_id'], unique=False)
    op.create_index('idx_documents_status', 'documents', ['status'], unique=False)
    op.create_index('idx_document_chunks_document_id', 'document_chunks', ['document_id'], unique=False)
    op.create_index('idx_clauses_document_id', 'clauses', ['document_id'], unique=False)
    op.create_index('idx_analyses_document_id', 'analyses', ['document_id'], unique=False)
    op.create_index('idx_playbooks_org_id', 'playbooks', ['org_id'], unique=False)
    op.create_index('idx_usage_records_org_period', 'usage_records', ['org_id', 'period_start', 'period_end'], unique=False)
    op.create_index('idx_audits_org_created', 'audits', ['org_id', 'created_at'], unique=False)
    
    # Create unique constraints
    op.create_index('ux_document_chunks_doc_chunk', 'document_chunks', ['document_id', 'chunk_no'], unique=True)
    op.create_index('ux_documents_org_hash', 'documents', ['org_id', 'file_hash'], unique=True)
    
    # Create vector index for embeddings (will be created after data is inserted)
    op.execute("CREATE INDEX idx_document_chunks_embedding ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)")
    
    # Create unique index for Stripe event idempotency
    op.execute("CREATE UNIQUE INDEX ux_events_stripe_id ON audits ((payload_json->>'stripe_event_id')) WHERE payload_json->>'stripe_event_id' IS NOT NULL")
    
    # Enable Row Level Security
    op.execute("ALTER TABLE orgs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE documents ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE clauses ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE analyses ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE playbooks ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE usage_records ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audits ENABLE ROW LEVEL SECURITY")
    
    # Create RLS Policies
    op.execute("""
        CREATE POLICY documents_org_rls ON documents 
        USING (org_id::text = current_setting('app.current_org', true))
    """)
    
    op.execute("""
        CREATE POLICY document_chunks_org_rls ON document_chunks 
        USING ((SELECT org_id FROM documents WHERE id = document_id)::text = current_setting('app.current_org', true))
    """)
    
    op.execute("""
        CREATE POLICY clauses_org_rls ON clauses 
        USING ((SELECT org_id FROM documents WHERE id = document_id)::text = current_setting('app.current_org', true))
    """)
    
    op.execute("""
        CREATE POLICY analyses_org_rls ON analyses 
        USING ((SELECT org_id FROM documents WHERE id = document_id)::text = current_setting('app.current_org', true))
    """)
    
    op.execute("""
        CREATE POLICY playbooks_org_rls ON playbooks 
        USING (org_id::text = current_setting('app.current_org', true))
    """)
    
    op.execute("""
        CREATE POLICY usage_records_org_rls ON usage_records 
        USING (org_id::text = current_setting('app.current_org', true))
    """)
    
    op.execute("""
        CREATE POLICY audits_org_rls ON audits 
        USING (org_id::text = current_setting('app.current_org', true))
    """)


def downgrade() -> None:
    # Drop RLS policies
    op.execute("DROP POLICY IF EXISTS documents_org_rls ON documents")
    op.execute("DROP POLICY IF EXISTS document_chunks_org_rls ON document_chunks")
    op.execute("DROP POLICY IF EXISTS clauses_org_rls ON clauses")
    op.execute("DROP POLICY IF EXISTS analyses_org_rls ON analyses")
    op.execute("DROP POLICY IF EXISTS playbooks_org_rls ON playbooks")
    op.execute("DROP POLICY IF EXISTS usage_records_org_rls ON usage_records")
    op.execute("DROP POLICY IF EXISTS audits_org_rls ON audits")
    
    # Disable RLS
    op.execute("ALTER TABLE orgs DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE documents DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE document_chunks DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE clauses DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE analyses DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE playbooks DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE usage_records DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audits DISABLE ROW LEVEL SECURITY")
    
    # Drop tables in reverse order
    op.drop_table('document_chunks')
    op.drop_table('clauses')
    op.drop_table('analyses')
    op.drop_table('audits')
    op.drop_table('usage_records')
    op.drop_table('playbooks')
    op.drop_table('documents')
    op.drop_table('subscriptions')
    op.drop_table('users')
    op.drop_table('orgs')
    
    # Drop extensions (optional, as they might be used by other databases)
    # op.execute("DROP EXTENSION IF EXISTS vector")
    # op.execute("DROP EXTENSION IF EXISTS pgcrypto")
