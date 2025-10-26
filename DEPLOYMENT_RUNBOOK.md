# LexiScan Deployment Runbook

This runbook provides step-by-step procedures for deploying, monitoring, and troubleshooting LexiScan in production environments.

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Staging Deployment](#staging-deployment)
3. [Production Deployment](#production-deployment)
4. [Post-Deployment Verification](#post-deployment-verification)
5. [Rollback Procedures](#rollback-procedures)
6. [Monitoring and Alerting](#monitoring-and-alerting)
7. [Troubleshooting](#troubleshooting)
8. [Emergency Procedures](#emergency-procedures)

## Pre-Deployment Checklist

### Code Quality Checks
- [ ] All tests pass (unit, integration, end-to-end)
- [ ] Code review completed and approved
- [ ] Security scan completed with no critical issues
- [ ] Performance benchmarks meet requirements
- [ ] Documentation updated

### Infrastructure Readiness
- [ ] AWS credentials configured and tested
- [ ] Terraform state is clean and up-to-date
- [ ] Docker images built and pushed to ECR
- [ ] Database migrations tested
- [ ] External service dependencies verified

### Configuration Validation
- [ ] Environment variables configured
- [ ] Secrets stored in AWS Secrets Manager
- [ ] Feature flags configured appropriately
- [ ] Monitoring and alerting configured
- [ ] Backup procedures verified

### Team Coordination
- [ ] Deployment window scheduled and communicated
- [ ] On-call engineer identified
- [ ] Rollback plan reviewed
- [ ] Stakeholders notified

## Staging Deployment

### 1. Deploy to Staging Environment

```bash
# Deploy staging environment
./scripts/deploy-staging.sh

# Seed with test data
./scripts/seed-staging-data.sh

# Run validation tests
./scripts/validate-deployment.sh -e staging
```

### 2. Staging Validation

```bash
# Run smoke tests
./scripts/smoke-tests.sh -u http://localhost:80 -e staging

# Run integration tests
./scripts/integration-tests.sh -u http://localhost:80 -e staging

# Manual testing checklist
```

#### Manual Testing Checklist
- [ ] User registration and login
- [ ] Document upload and processing
- [ ] AI-powered analysis and Q&A
- [ ] Billing and subscription management
- [ ] Admin functions and user management
- [ ] Performance under load

### 3. Staging Sign-off

- [ ] All automated tests pass
- [ ] Manual testing completed
- [ ] Performance metrics acceptable
- [ ] Security validation completed
- [ ] Product owner approval received

## Production Deployment

### 1. Pre-Production Steps

```bash
# Verify staging is healthy
./scripts/validate-deployment.sh -e staging

# Create release tag
./scripts/release.sh -t minor  # or patch/major

# Generate changelog
./scripts/generate-changelog.sh
```

### 2. Production Deployment

#### Option A: Automated CI/CD (Recommended)
```bash
# Push release tag to trigger CI/CD
git push origin v1.2.3
```

#### Option B: Manual Deployment
```bash
# Deploy to production
./scripts/deploy-production.sh

# Monitor deployment progress
watch -n 30 'aws ecs describe-services --cluster lexiscan-production-cluster --services lexiscan-production-backend lexiscan-production-frontend --query "services[*].[serviceName,runningCount,desiredCount,deployments[0].status]" --output table'
```

### 3. Deployment Monitoring

Monitor the following during deployment:

#### ECS Service Health
```bash
# Check service status
aws ecs describe-services \
  --cluster lexiscan-production-cluster \
  --services lexiscan-production-backend lexiscan-production-frontend

# Check task health
aws ecs list-tasks \
  --cluster lexiscan-production-cluster \
  --service-name lexiscan-production-backend
```

#### Application Health
```bash
# Health check endpoints
curl -f https://lexiscan.ai/api/health
curl -f https://lexiscan.ai/api/health/detailed
curl -f https://lexiscan.ai/api/ready
```

#### CloudWatch Metrics
- CPU and memory utilization
- Request count and response times
- Error rates
- Database connections

## Post-Deployment Verification

### 1. Automated Verification

```bash
# Run comprehensive validation
./scripts/validate-deployment.sh -e production -u https://lexiscan.ai

# Run smoke tests
./scripts/smoke-tests.sh -u https://lexiscan.ai -e production
```

### 2. Manual Verification

#### Critical User Workflows
- [ ] User can register and login
- [ ] Document upload works correctly
- [ ] AI analysis produces results
- [ ] RAG queries return accurate responses
- [ ] Billing integration functions properly
- [ ] Admin features accessible

#### Performance Verification
- [ ] Response times < 2s for 95th percentile
- [ ] Error rate < 1%
- [ ] Database query performance acceptable
- [ ] Memory usage within limits

#### Security Verification
- [ ] HTTPS enforced
- [ ] Security headers present
- [ ] Authentication working
- [ ] Authorization rules enforced

### 3. Monitoring Setup

#### CloudWatch Alarms
- High error rate (>5% for 5 minutes)
- High response time (>2s P95 for 5 minutes)
- High CPU usage (>80% for 10 minutes)
- High memory usage (>80% for 10 minutes)
- Database connection issues

#### Log Monitoring
- Application error logs
- Security-related events
- Performance anomalies
- User behavior patterns

## Rollback Procedures

### When to Rollback

Immediate rollback triggers:
- Error rate > 10%
- Critical functionality broken
- Security vulnerability exposed
- Data corruption detected
- Performance degradation > 50%

### Automated Rollback

The deployment script includes automatic rollback on failure:

```bash
# Rollback is automatic on deployment failure
# Monitor rollback progress in deployment logs
```

### Manual Rollback

#### Emergency Rollback
```bash
# Quick rollback to previous version
./scripts/rollback-production.sh --force

# Rollback to specific version
./scripts/rollback-production.sh --revision 5
```

#### Planned Rollback
```bash
# Show rollback plan
./scripts/rollback-production.sh --dry-run

# Execute rollback with confirmation
./scripts/rollback-production.sh
```

### Post-Rollback Actions

1. **Verify System Health**
   ```bash
   ./scripts/validate-deployment.sh -e production
   ```

2. **Communicate Status**
   - Notify stakeholders
   - Update status page
   - Document incident

3. **Root Cause Analysis**
   - Collect logs and metrics
   - Identify failure cause
   - Plan remediation

## Monitoring and Alerting

### Key Metrics to Monitor

#### Application Metrics
- Request rate and response times
- Error rates by endpoint
- User authentication success rate
- Document processing success rate
- AI query response times

#### Infrastructure Metrics
- ECS service health and task count
- RDS database performance
- Redis cache hit rates
- S3 request metrics
- ALB target health

#### Business Metrics
- User registrations
- Document uploads
- AI queries performed
- Subscription conversions
- Revenue metrics

### Alert Escalation

#### Severity Levels

**Critical (P1)**
- Service completely down
- Data loss or corruption
- Security breach
- Response: Immediate (< 5 minutes)

**High (P2)**
- Significant feature degradation
- High error rates
- Performance issues
- Response: Within 30 minutes

**Medium (P3)**
- Minor feature issues
- Elevated error rates
- Non-critical performance issues
- Response: Within 2 hours

**Low (P4)**
- Cosmetic issues
- Minor performance degradation
- Response: Next business day

### Monitoring Tools

#### AWS CloudWatch
- Custom metrics and alarms
- Log aggregation and analysis
- Dashboard creation

#### Application Performance Monitoring
- OpenTelemetry tracing
- Custom business metrics
- User experience monitoring

## Troubleshooting

### Common Issues

#### Deployment Failures

**Symptom**: ECS service fails to start new tasks
```bash
# Check service events
aws ecs describe-services --cluster lexiscan-production-cluster --services lexiscan-production-backend

# Check task definition
aws ecs describe-task-definition --task-definition lexiscan-backend:latest

# Check task logs
aws logs tail /aws/ecs/lexiscan-backend --follow
```

**Symptom**: Health checks failing
```bash
# Check application logs
aws logs filter-log-events --log-group-name /aws/ecs/lexiscan-backend --filter-pattern "ERROR"

# Test health endpoints directly
curl -v https://lexiscan.ai/api/health/detailed
```

#### Performance Issues

**Symptom**: High response times
```bash
# Check CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name TargetResponseTime \
  --dimensions Name=LoadBalancer,Value=app/lexiscan-prod-alb/1234567890 \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-01T23:59:59Z \
  --period 300 \
  --statistics Average

# Check database performance
aws rds describe-db-instances --db-instance-identifier lexiscan-prod-db
```

**Symptom**: High memory usage
```bash
# Check ECS task metrics
aws ecs describe-tasks --cluster lexiscan-production-cluster --tasks <task-arn>

# Scale up if needed
aws ecs update-service \
  --cluster lexiscan-production-cluster \
  --service lexiscan-production-backend \
  --desired-count 4
```

#### Database Issues

**Symptom**: Connection timeouts
```bash
# Check RDS metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name DatabaseConnections \
  --dimensions Name=DBInstanceIdentifier,Value=lexiscan-prod-db

# Check connection pool settings
# Review application configuration
```

**Symptom**: Slow queries
```bash
# Enable slow query log
aws rds modify-db-instance \
  --db-instance-identifier lexiscan-prod-db \
  --db-parameter-group-name lexiscan-prod-params \
  --apply-immediately

# Analyze slow queries
# Review database indexes
```

### Log Analysis

#### Application Logs
```bash
# Search for errors
aws logs filter-log-events \
  --log-group-name /aws/ecs/lexiscan-backend \
  --filter-pattern "ERROR" \
  --start-time 1640995200000

# Search for specific patterns
aws logs filter-log-events \
  --log-group-name /aws/ecs/lexiscan-backend \
  --filter-pattern "[timestamp, request_id, level=ERROR, ...]"
```

#### Access Logs
```bash
# Analyze ALB access logs
aws s3 cp s3://lexiscan-alb-logs/AWSLogs/123456789012/elasticloadbalancing/us-east-1/ . --recursive

# Parse logs for errors
grep "5[0-9][0-9]" access.log | head -20
```

## Emergency Procedures

### Service Outage Response

#### Immediate Actions (0-5 minutes)
1. **Assess Impact**
   - Check monitoring dashboards
   - Verify scope of outage
   - Determine user impact

2. **Initial Response**
   - Activate incident response team
   - Create incident ticket
   - Begin status page updates

3. **Quick Fixes**
   - Check for obvious issues
   - Restart services if appropriate
   - Scale up resources if needed

#### Short-term Actions (5-30 minutes)
1. **Detailed Investigation**
   - Analyze logs and metrics
   - Check recent deployments
   - Review infrastructure changes

2. **Mitigation**
   - Implement temporary fixes
   - Route traffic if possible
   - Consider rollback

3. **Communication**
   - Update stakeholders
   - Provide regular status updates
   - Document actions taken

#### Long-term Actions (30+ minutes)
1. **Root Cause Analysis**
   - Deep dive investigation
   - Identify contributing factors
   - Document timeline

2. **Permanent Fix**
   - Implement proper solution
   - Test thoroughly
   - Deploy fix

3. **Post-Incident Review**
   - Conduct blameless postmortem
   - Identify improvements
   - Update procedures

### Data Recovery Procedures

#### Database Recovery
```bash
# Restore from automated backup
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier lexiscan-prod-db-restored \
  --db-snapshot-identifier lexiscan-prod-db-snapshot-20240101

# Point-in-time recovery
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier lexiscan-prod-db \
  --target-db-instance-identifier lexiscan-prod-db-restored \
  --restore-time 2024-01-01T12:00:00Z
```

#### File Recovery
```bash
# Restore from S3 versioning
aws s3api list-object-versions --bucket lexiscan-documents-prod --prefix documents/

# Restore specific version
aws s3api get-object \
  --bucket lexiscan-documents-prod \
  --key documents/example.pdf \
  --version-id <version-id> \
  restored-example.pdf
```

### Security Incident Response

#### Immediate Actions
1. **Isolate Affected Systems**
   - Block suspicious traffic
   - Disable compromised accounts
   - Isolate affected services

2. **Assess Damage**
   - Check for data access
   - Review audit logs
   - Identify scope of breach

3. **Contain Threat**
   - Patch vulnerabilities
   - Update security rules
   - Monitor for continued activity

#### Follow-up Actions
1. **Investigation**
   - Forensic analysis
   - Timeline reconstruction
   - Impact assessment

2. **Recovery**
   - Restore from clean backups
   - Update security measures
   - Verify system integrity

3. **Communication**
   - Notify affected users
   - Report to authorities if required
   - Update security policies

## Contact Information

### On-Call Rotation
- Primary: [On-call engineer]
- Secondary: [Backup engineer]
- Escalation: [Engineering manager]

### External Contacts
- AWS Support: [Support case URL]
- Security Team: [Security contact]
- Legal/Compliance: [Legal contact]

### Communication Channels
- Incident Slack: #incidents
- Status Page: https://status.lexiscan.ai
- Customer Support: support@lexiscan.ai

---

**Last Updated**: [Date]
**Version**: 1.0
**Owner**: DevOps Team