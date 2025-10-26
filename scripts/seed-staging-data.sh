#!/bin/bash

# Staging Data Seeding Script
# Populates staging environment with production-like test data

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration
API_BASE_URL="http://localhost:8001"
FRONTEND_URL="http://localhost:3001"

# Check if staging is running
check_staging_running() {
    print_status "Checking if staging environment is running..."
    
    if ! curl -f "$API_BASE_URL/api/health" &>/dev/null; then
        print_error "Staging environment is not running. Please start it first with:"
        print_error "  ./scripts/deploy-staging.sh"
        exit 1
    fi
    
    print_success "Staging environment is running"
}

# Create test organizations
create_organizations() {
    print_status "Creating test organizations..."
    
    # Create organizations via database
    docker-compose -f docker-compose.staging.yml exec -T postgres psql -U lexiscan -d lexiscan_staging << 'EOF'
-- Create test organizations
INSERT INTO orgs (id, name, created_at) VALUES 
    ('550e8400-e29b-41d4-a716-446655440001', 'Acme Legal Corp', NOW()),
    ('550e8400-e29b-41d4-a716-446655440002', 'Beta Law Firm', NOW()),
    ('550e8400-e29b-41d4-a716-446655440003', 'Gamma Enterprises', NOW())
ON CONFLICT (id) DO NOTHING;
EOF
    
    print_success "Test organizations created"
}

# Create test users
create_users() {
    print_status "Creating test users..."
    
    # Create users via database
    docker-compose -f docker-compose.staging.yml exec -T postgres psql -U lexiscan -d lexiscan_staging << 'EOF'
-- Create test users
INSERT INTO users (id, org_id, email, role, provider, created_at) VALUES 
    ('550e8400-e29b-41d4-a716-446655440011', '550e8400-e29b-41d4-a716-446655440001', 'admin@acmelegal.com', 'admin', 'email', NOW()),
    ('550e8400-e29b-41d4-a716-446655440012', '550e8400-e29b-41d4-a716-446655440001', 'lawyer@acmelegal.com', 'reviewer', 'email', NOW()),
    ('550e8400-e29b-41d4-a716-446655440013', '550e8400-e29b-41d4-a716-446655440001', 'paralegal@acmelegal.com', 'viewer', 'email', NOW()),
    ('550e8400-e29b-41d4-a716-446655440021', '550e8400-e29b-41d4-a716-446655440002', 'partner@betalaw.com', 'admin', 'email', NOW()),
    ('550e8400-e29b-41d4-a716-446655440022', '550e8400-e29b-41d4-a716-446655440002', 'associate@betalaw.com', 'reviewer', 'email', NOW()),
    ('550e8400-e29b-41d4-a716-446655440031', '550e8400-e29b-41d4-a716-446655440003', 'legal@gamma.com', 'admin', 'email', NOW())
ON CONFLICT (id) DO NOTHING;
EOF
    
    print_success "Test users created"
}

# Create test subscriptions
create_subscriptions() {
    print_status "Creating test subscriptions..."
    
    docker-compose -f docker-compose.staging.yml exec -T postgres psql -U lexiscan -d lexiscan_staging << 'EOF'
-- Create test subscriptions
INSERT INTO subscriptions (id, org_id, stripe_customer_id, plan, status, usage_limits, created_at) VALUES 
    ('550e8400-e29b-41d4-a716-446655440101', '550e8400-e29b-41d4-a716-446655440001', 'cus_test_acme', 'enterprise', 'active', '{"pages_per_month": 10000, "queries_per_month": 5000}', NOW()),
    ('550e8400-e29b-41d4-a716-446655440102', '550e8400-e29b-41d4-a716-446655440002', 'cus_test_beta', 'pro', 'active', '{"pages_per_month": 1500, "queries_per_month": 1000}', NOW()),
    ('550e8400-e29b-41d4-a716-446655440103', '550e8400-e29b-41d4-a716-446655440003', 'cus_test_gamma', 'free', 'active', '{"pages_per_month": 50, "queries_per_month": 100}', NOW())
ON CONFLICT (id) DO NOTHING;
EOF
    
    print_success "Test subscriptions created"
}

# Create test playbooks
create_playbooks() {
    print_status "Creating test playbooks..."
    
    docker-compose -f docker-compose.staging.yml exec -T postgres psql -U lexiscan -d lexiscan_staging << 'EOF'
-- Create test playbooks
INSERT INTO playbooks (id, org_id, name, rules_json, is_default, created_at) VALUES 
    ('550e8400-e29b-41d4-a716-446655440201', '550e8400-e29b-41d4-a716-446655440001', 'Standard Contract Review', 
     '{"rules": [
       {"type": "required_clause", "name": "Indemnification", "weight": 10},
       {"type": "required_clause", "name": "Liability Cap", "weight": 8},
       {"type": "required_clause", "name": "Termination", "weight": 7},
       {"type": "risk_keyword", "keywords": ["unlimited liability", "personal guarantee"], "risk_level": "high"}
     ]}', true, NOW()),
    ('550e8400-e29b-41d4-a716-446655440202', '550e8400-e29b-41d4-a716-446655440002', 'Employment Agreement Review', 
     '{"rules": [
       {"type": "required_clause", "name": "Non-Compete", "weight": 9},
       {"type": "required_clause", "name": "Confidentiality", "weight": 8},
       {"type": "required_clause", "name": "Intellectual Property", "weight": 7}
     ]}', true, NOW())
ON CONFLICT (id) DO NOTHING;
EOF
    
    print_success "Test playbooks created"
}

# Create sample documents
create_sample_documents() {
    print_status "Creating sample documents..."
    
    # Create sample document content
    mkdir -p /tmp/staging-docs
    
    # Sample NDA
    cat > /tmp/staging-docs/sample-nda.txt << 'EOF'
NON-DISCLOSURE AGREEMENT

This Non-Disclosure Agreement ("Agreement") is entered into on [DATE] by and between Acme Legal Corp ("Disclosing Party") and [RECIPIENT] ("Receiving Party").

1. CONFIDENTIAL INFORMATION
The Disclosing Party may disclose certain confidential and proprietary information to the Receiving Party.

2. OBLIGATIONS
The Receiving Party agrees to:
- Keep all confidential information strictly confidential
- Not disclose to any third parties
- Use information solely for evaluation purposes

3. TERM
This Agreement shall remain in effect for a period of two (2) years from the date of execution.

4. INDEMNIFICATION
The Receiving Party agrees to indemnify and hold harmless the Disclosing Party from any damages arising from breach of this Agreement.

5. TERMINATION
Either party may terminate this Agreement with thirty (30) days written notice.

6. GOVERNING LAW
This Agreement shall be governed by the laws of [STATE].
EOF

    # Sample Service Agreement
    cat > /tmp/staging-docs/sample-service-agreement.txt << 'EOF'
SERVICE AGREEMENT

This Service Agreement ("Agreement") is entered into between Beta Law Firm ("Provider") and [CLIENT] ("Client").

1. SERVICES
Provider agrees to provide legal consulting services as described in Exhibit A.

2. COMPENSATION
Client agrees to pay Provider $500 per hour for services rendered.

3. LIABILITY LIMITATION
Provider's liability shall be limited to the amount of fees paid under this Agreement.

4. INTELLECTUAL PROPERTY
All work product created by Provider shall remain the property of Client.

5. CONFIDENTIALITY
Both parties agree to maintain confidentiality of all information exchanged.

6. TERMINATION
This Agreement may be terminated by either party with fifteen (15) days written notice.

7. DISPUTE RESOLUTION
Any disputes shall be resolved through binding arbitration.
EOF

    # Insert documents into database
    docker-compose -f docker-compose.staging.yml exec -T postgres psql -U lexiscan -d lexiscan_staging << 'EOF'
-- Create sample documents
INSERT INTO documents (id, org_id, title, s3_key, file_type, file_size, file_hash, status, uploaded_by, created_at, processed_at) VALUES 
    ('550e8400-e29b-41d4-a716-446655440301', '550e8400-e29b-41d4-a716-446655440001', 'Sample NDA Agreement', 'staging/sample-nda.txt', 'txt', 1024, 'hash1', 'completed', '550e8400-e29b-41d4-a716-446655440011', NOW(), NOW()),
    ('550e8400-e29b-41d4-a716-446655440302', '550e8400-e29b-41d4-a716-446655440002', 'Service Agreement Template', 'staging/sample-service-agreement.txt', 'txt', 1536, 'hash2', 'completed', '550e8400-e29b-41d4-a716-446655440021', NOW(), NOW())
ON CONFLICT (id) DO NOTHING;
EOF

    # Create document chunks for vector search
    docker-compose -f docker-compose.staging.yml exec -T postgres psql -U lexiscan -d lexiscan_staging << 'EOF'
-- Create document chunks
INSERT INTO document_chunks (id, document_id, chunk_no, text, page, metadata, created_at) VALUES 
    ('550e8400-e29b-41d4-a716-446655440401', '550e8400-e29b-41d4-a716-446655440301', 1, 'This Non-Disclosure Agreement is entered into by and between Acme Legal Corp and the Receiving Party. The Disclosing Party may disclose certain confidential and proprietary information.', 1, '{"section": "introduction"}', NOW()),
    ('550e8400-e29b-41d4-a716-446655440402', '550e8400-e29b-41d4-a716-446655440301', 2, 'The Receiving Party agrees to keep all confidential information strictly confidential and not disclose to any third parties. Information shall be used solely for evaluation purposes.', 1, '{"section": "obligations"}', NOW()),
    ('550e8400-e29b-41d4-a716-446655440403', '550e8400-e29b-41d4-a716-446655440301', 3, 'The Receiving Party agrees to indemnify and hold harmless the Disclosing Party from any damages arising from breach of this Agreement.', 1, '{"section": "indemnification"}', NOW()),
    ('550e8400-e29b-41d4-a716-446655440404', '550e8400-e29b-41d4-a716-446655440302', 1, 'This Service Agreement is entered into between Beta Law Firm as Provider and Client. Provider agrees to provide legal consulting services.', 1, '{"section": "services"}', NOW()),
    ('550e8400-e29b-41d4-a716-446655440405', '550e8400-e29b-41d4-a716-446655440302', 2, 'Client agrees to pay Provider $500 per hour for services rendered. Providers liability shall be limited to the amount of fees paid under this Agreement.', 1, '{"section": "compensation"}', NOW())
ON CONFLICT (id) DO NOTHING;
EOF

    print_success "Sample documents created"
    
    # Clean up temp files
    rm -rf /tmp/staging-docs
}

# Create sample analyses
create_sample_analyses() {
    print_status "Creating sample analyses..."
    
    docker-compose -f docker-compose.staging.yml exec -T postgres psql -U lexiscan -d lexiscan_staging << 'EOF'
-- Create sample analyses
INSERT INTO analyses (id, document_id, playbook_id, risk_score, summary_json, recommendations, created_at) VALUES 
    ('550e8400-e29b-41d4-a716-446655440501', '550e8400-e29b-41d4-a716-446655440301', '550e8400-e29b-41d4-a716-446655440201', 75, 
     '{"overall_risk": "medium", "missing_clauses": ["Liability Cap"], "found_clauses": ["Indemnification", "Termination"], "risk_factors": ["Standard indemnification clause present"]}',
     '[{"type": "missing_clause", "description": "Consider adding a liability cap clause to limit exposure", "priority": "medium"}]', NOW()),
    ('550e8400-e29b-41d4-a716-446655440502', '550e8400-e29b-41d4-a716-446655440302', '550e8400-e29b-41d4-a716-446655440202', 60,
     '{"overall_risk": "low", "missing_clauses": ["Non-Compete"], "found_clauses": ["Confidentiality", "Intellectual Property"], "risk_factors": ["Liability limitation present"]}',
     '[{"type": "missing_clause", "description": "Consider adding non-compete clause if applicable", "priority": "low"}]', NOW())
ON CONFLICT (id) DO NOTHING;
EOF

    print_success "Sample analyses created"
}

# Create usage records
create_usage_records() {
    print_status "Creating usage records..."
    
    docker-compose -f docker-compose.staging.yml exec -T postgres psql -U lexiscan -d lexiscan_staging << 'EOF'
-- Create usage records
INSERT INTO usage_records (id, org_id, usage_type, amount, period_start, period_end, created_at) VALUES 
    ('550e8400-e29b-41d4-a716-446655440601', '550e8400-e29b-41d4-a716-446655440001', 'pages_analyzed', 150, DATE_TRUNC('month', CURRENT_DATE), DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month' - INTERVAL '1 day', NOW()),
    ('550e8400-e29b-41d4-a716-446655440602', '550e8400-e29b-41d4-a716-446655440001', 'queries_made', 45, DATE_TRUNC('month', CURRENT_DATE), DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month' - INTERVAL '1 day', NOW()),
    ('550e8400-e29b-41d4-a716-446655440603', '550e8400-e29b-41d4-a716-446655440002', 'pages_analyzed', 75, DATE_TRUNC('month', CURRENT_DATE), DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month' - INTERVAL '1 day', NOW()),
    ('550e8400-e29b-41d4-a716-446655440604', '550e8400-e29b-41d4-a716-446655440002', 'queries_made', 23, DATE_TRUNC('month', CURRENT_DATE), DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month' - INTERVAL '1 day', NOW()),
    ('550e8400-e29b-41d4-a716-446655440605', '550e8400-e29b-41d4-a716-446655440003', 'pages_analyzed', 12, DATE_TRUNC('month', CURRENT_DATE), DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month' - INTERVAL '1 day', NOW()),
    ('550e8400-e29b-41d4-a716-446655440606', '550e8400-e29b-41d4-a716-446655440003', 'queries_made', 8, DATE_TRUNC('month', CURRENT_DATE), DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month' - INTERVAL '1 day', NOW())
ON CONFLICT (id) DO NOTHING;
EOF

    print_success "Usage records created"
}

# Create audit logs
create_audit_logs() {
    print_status "Creating audit logs..."
    
    docker-compose -f docker-compose.staging.yml exec -T postgres psql -U lexiscan -d lexiscan_staging << 'EOF'
-- Create audit logs
INSERT INTO audits (id, org_id, user_id, action, resource_type, resource_id, payload_json, ip_address, created_at) VALUES 
    ('550e8400-e29b-41d4-a716-446655440701', '550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440011', 'document_upload', 'document', '550e8400-e29b-41d4-a716-446655440301', '{"filename": "sample-nda.txt", "size": 1024}', '192.168.1.100', NOW() - INTERVAL '2 hours'),
    ('550e8400-e29b-41d4-a716-446655440702', '550e8400-e29b-41d4-a716-446655440001', '550e8400-e29b-41d4-a716-446655440012', 'document_analyze', 'analysis', '550e8400-e29b-41d4-a716-446655440501', '{"playbook": "Standard Contract Review", "risk_score": 75}', '192.168.1.101', NOW() - INTERVAL '1 hour'),
    ('550e8400-e29b-41d4-a716-446655440703', '550e8400-e29b-41d4-a716-446655440002', '550e8400-e29b-41d4-a716-446655440021', 'document_upload', 'document', '550e8400-e29b-41d4-a716-446655440302', '{"filename": "service-agreement.txt", "size": 1536}', '192.168.1.102', NOW() - INTERVAL '30 minutes'),
    ('550e8400-e29b-41d4-a716-446655440704', '550e8400-e29b-41d4-a716-446655440002', '550e8400-e29b-41d4-a716-446655440022', 'rag_query', 'query', NULL, '{"query": "What are the payment terms?", "response_length": 150}', '192.168.1.103', NOW() - INTERVAL '15 minutes')
ON CONFLICT (id) DO NOTHING;
EOF

    print_success "Audit logs created"
}

# Verify data creation
verify_data() {
    print_status "Verifying created data..."
    
    # Check counts
    docker-compose -f docker-compose.staging.yml exec -T postgres psql -U lexiscan -d lexiscan_staging << 'EOF'
SELECT 'Organizations' as table_name, COUNT(*) as count FROM orgs
UNION ALL
SELECT 'Users', COUNT(*) FROM users
UNION ALL
SELECT 'Subscriptions', COUNT(*) FROM subscriptions
UNION ALL
SELECT 'Playbooks', COUNT(*) FROM playbooks
UNION ALL
SELECT 'Documents', COUNT(*) FROM documents
UNION ALL
SELECT 'Document Chunks', COUNT(*) FROM document_chunks
UNION ALL
SELECT 'Analyses', COUNT(*) FROM analyses
UNION ALL
SELECT 'Usage Records', COUNT(*) FROM usage_records
UNION ALL
SELECT 'Audit Logs', COUNT(*) FROM audits;
EOF

    print_success "Data verification completed"
}

# Main function
main() {
    print_status "Starting staging data seeding..."
    
    check_staging_running
    create_organizations
    create_users
    create_subscriptions
    create_playbooks
    create_sample_documents
    create_sample_analyses
    create_usage_records
    create_audit_logs
    verify_data
    
    print_success "🌱 Staging data seeding completed successfully!"
    echo ""
    echo "Test accounts created:"
    echo "  admin@acmelegal.com (Admin - Acme Legal Corp)"
    echo "  lawyer@acmelegal.com (Reviewer - Acme Legal Corp)"
    echo "  paralegal@acmelegal.com (Viewer - Acme Legal Corp)"
    echo "  partner@betalaw.com (Admin - Beta Law Firm)"
    echo "  associate@betalaw.com (Reviewer - Beta Law Firm)"
    echo "  legal@gamma.com (Admin - Gamma Enterprises)"
    echo ""
    echo "Sample data includes:"
    echo "  - 3 organizations with different subscription plans"
    echo "  - 6 test users with different roles"
    echo "  - 2 sample documents with analysis results"
    echo "  - Usage records and audit logs"
    echo ""
    echo "You can now test the application with realistic data!"
}

# Run main function
main