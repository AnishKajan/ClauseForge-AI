# ClauseForge AWS to Azure Migration Checklist

## Pre-Migration Preparation

### ✅ Prerequisites
- [ ] Azure CLI installed and configured
- [ ] Azure subscription active (Pay-as-you-go)
- [ ] AWS CLI configured (for data migration)
- [ ] Docker installed (optional, ACR Tasks can build remotely)
- [ ] GitHub repository access
- [ ] Domain name ready (optional)

### ✅ Backup Current System
- [ ] Export AWS RDS database backup
- [ ] List all S3 objects and their metadata
- [ ] Document current AWS resource configurations
- [ ] Export CloudWatch logs if needed
- [ ] Save current environment variables

## Phase 1: Azure Infrastructure Setup

### ✅ Core Resources
- [ ] Create Azure Resource Group
- [ ] Set up Log Analytics Workspace
- [ ] Create Container Apps Environment
- [ ] Create Azure Container Registry
- [ ] Set up PostgreSQL Flexible Server
- [ ] Create Azure Cache for Redis
- [ ] Set up Blob Storage account and containers

### ✅ AI and Cognitive Services
- [ ] Create Document Intelligence resource
- [ ] Test Document Intelligence with sample documents
- [ ] Configure API keys and endpoints

### ✅ Security and Access
- [ ] Create Key Vault for secrets management
- [ ] Set up service principal for GitHub Actions
- [ ] Configure RBAC permissions
- [ ] Set up network security groups (if needed)

## Phase 2: Application Migration

### ✅ Code Updates
- [ ] Update backend requirements.txt with Azure SDKs
- [ ] Replace AWS S3 service with Azure Blob Storage
- [ ] Replace AWS Textract with Azure Document Intelligence
- [ ] Update configuration files for Azure
- [ ] Test storage migration service locally
- [ ] Update environment variable references

### ✅ Database Migration
- [ ] Enable pgvector extension on Azure PostgreSQL
- [ ] Export data from AWS RDS
- [ ] Import data to Azure PostgreSQL
- [ ] Verify data integrity
- [ ] Update connection strings

### ✅ Storage Migration
- [ ] Migrate documents from S3 to Blob Storage
- [ ] Verify file integrity (checksums)
- [ ] Update file references in database
- [ ] Test file upload/download functionality

## Phase 3: CI/CD Pipeline

### ✅ GitHub Actions Setup
- [ ] Create Azure service principal
- [ ] Add GitHub secrets for Azure credentials
- [ ] Update workflow to use Azure Container Registry
- [ ] Configure Container Apps deployment
- [ ] Set up Azure Static Web Apps for frontend
- [ ] Test deployment pipeline

### ✅ GitHub Secrets Required
- [ ] `AZURE_CREDENTIALS` (service principal JSON)
- [ ] `AZURE_RG` (resource group name)
- [ ] `AZURE_ACR_NAME` (container registry name)
- [ ] `AZURE_APP_NAME` (container app name)
- [ ] `CLAUDE_API_KEY` (Anthropic API key)
- [ ] `STRIPE_SECRET_KEY` (Stripe secret key)
- [ ] `JWT_SECRET` (JWT signing key)
- [ ] `AZURE_STATIC_WEB_APPS_API_TOKEN` (for frontend deployment)

## Phase 4: Testing and Validation

### ✅ Functional Testing
- [ ] Test user authentication and authorization
- [ ] Test document upload functionality
- [ ] Test document processing and text extraction
- [ ] Test AI analysis features
- [ ] Test billing and subscription features
- [ ] Test admin and organization features

### ✅ Performance Testing
- [ ] Load test API endpoints
- [ ] Test Container Apps scaling
- [ ] Verify database performance
- [ ] Test file upload/download speeds
- [ ] Monitor memory and CPU usage

### ✅ Security Testing
- [ ] Verify HTTPS configuration
- [ ] Test authentication flows
- [ ] Validate CORS settings
- [ ] Check for exposed secrets
- [ ] Test rate limiting

## Phase 5: Go-Live

### ✅ DNS and Domain
- [ ] Update DNS records to point to Azure
- [ ] Configure custom domain (if applicable)
- [ ] Set up SSL certificates
- [ ] Test domain resolution

### ✅ Monitoring and Alerting
- [ ] Configure Azure Monitor alerts
- [ ] Set up log aggregation
- [ ] Configure health checks
- [ ] Set up cost monitoring
- [ ] Configure backup schedules

### ✅ Documentation
- [ ] Update deployment documentation
- [ ] Update environment setup guides
- [ ] Document new Azure resource configurations
- [ ] Update troubleshooting guides

## Phase 6: Post-Migration

### ✅ Optimization
- [ ] Review and optimize Container Apps scaling rules
- [ ] Optimize database performance
- [ ] Review storage costs and lifecycle policies
- [ ] Fine-tune monitoring and alerting

### ✅ AWS Cleanup
- [ ] Verify all functionality works on Azure
- [ ] Stop AWS services (but keep for rollback initially)
- [ ] Delete AWS resources after 30-day verification period
- [ ] Cancel AWS services and subscriptions

### ✅ Team Training
- [ ] Train team on Azure portal
- [ ] Document new operational procedures
- [ ] Update incident response procedures
- [ ] Share new monitoring dashboards

## Rollback Plan

### ✅ If Migration Fails
- [ ] Revert DNS to AWS
- [ ] Restart AWS services
- [ ] Restore database from backup if needed
- [ ] Update GitHub Actions to use AWS again
- [ ] Communicate rollback to stakeholders

## Success Criteria

### ✅ Migration Complete When:
- [ ] All functionality works on Azure
- [ ] Performance meets or exceeds AWS baseline
- [ ] Security posture is maintained or improved
- [ ] Costs are within expected range
- [ ] Team is comfortable with new platform
- [ ] Monitoring and alerting are functional
- [ ] Backup and disaster recovery tested

## Cost Monitoring

### ✅ Expected Monthly Costs (Azure)
- Container Apps: $30-80 (scale-to-zero)
- PostgreSQL Flexible: $25-50
- Blob Storage: $5-15
- Redis Cache: $15-30
- Document Intelligence: $10-25 (usage-based)
- **Total: $85-200/month**

### ✅ Cost Optimization
- [ ] Set up cost alerts
- [ ] Review resource utilization weekly
- [ ] Optimize Container Apps scaling
- [ ] Use reserved instances for predictable workloads
- [ ] Implement storage lifecycle policies

## Timeline

- **Week 1**: Infrastructure setup and code migration
- **Week 2**: Testing and validation
- **Week 3**: Go-live and monitoring setup
- **Week 4**: Optimization and AWS cleanup

## Emergency Contacts

- **Azure Support**: [Azure Support Portal]
- **GitHub Actions**: [GitHub Support]
- **Team Lead**: [Contact Information]
- **DevOps Engineer**: [Contact Information]

---

**Migration Status**: ⏳ In Progress
**Last Updated**: [Date]
**Next Review**: [Date]