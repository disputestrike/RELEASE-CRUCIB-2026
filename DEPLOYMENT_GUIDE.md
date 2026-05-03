# CrucibAI Production Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying CrucibAI to production on Railway.

**Deployment Timeline:** 5-7 days
**Estimated Cost:** $23-53/month
**Status:** Production-Ready ✅

---

## Phase 1: Infrastructure Setup (Day 1)

### 1.1 Railway Account Setup

```bash
# Create Railway account
# Visit: https://railway.app

# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Create new project
railway init
```

### 1.2 Database Configuration

```bash
# Create PostgreSQL database on Railway
railway add --plugin postgres

# Get database URL
railway variables

# Copy DATABASE_URL to .env.production
```

### 1.3 Redis Setup (Caching)

```bash
# Add Redis to Railway
railway add --plugin redis

# Get Redis URL
railway variables

# Copy REDIS_URL to .env.production
```

### 1.4 Environment Variables

```bash
# Copy template to production
cp .env.production.template .env.production

# Fill in all required secrets:
# - JWT_SECRET (generate: openssl rand -hex 16)
# - API_KEY_ENCRYPTION_KEY (generate: openssl rand -hex 16)
# - PAYPAL_MODE=sandbox (use live after production approval)
# - PAYPAL_CLIENT_ID (from PayPal developer dashboard)
# - PAYPAL_CLIENT_SECRET (from PayPal developer dashboard)
# - APP_URL=https://your-production-domain.com
# - PayPal webhook URL: APP_URL/api/billing/webhook/paypal
# - OAUTH_GOOGLE_CLIENT_ID (from Google Cloud)
# - OAUTH_GOOGLE_CLIENT_SECRET (from Google Cloud)
# - SENTRY_DSN (from Sentry.io)
# - AWS credentials (for backups)
# - SMTP credentials (you will provide)

# Deploy environment variables
railway variables set --file .env.production
```

---

## Phase 2: Database Initialization (Day 1)

### 2.1 Run Migrations

```bash
# Connect to production database
railway connect postgres

# Run initialization script
python3 backend/database_init.py

# Verify tables created
\dt
```

### 2.2 Seed Initial Data

```bash
# Admin user created automatically
# Email: admin@crucibai.app
# Username: admin
# Role: admin
```

---

## Phase 3: Backend Deployment (Day 2)

### 3.1 Build Backend

```bash
# Install dependencies
npm install

# Build backend
npm run build

# Test locally
npm start
```

### 3.2 Deploy to Railway

```bash
# Connect repository
railway link

# Deploy backend
railway up

# Monitor deployment
railway logs --follow
```

### 3.3 Verify Backend

```bash
# Check health endpoint
curl https://your-app.railway.app/health

# Expected response:
# {
#   "status": "healthy",
#   "database": "healthy",
#   "redis": "healthy",
#   "timestamp": "2026-02-24T..."
# }
```

---

## Phase 4: Frontend Deployment (Day 2)

### 4.1 Build Frontend

```bash
cd frontend

# Install dependencies
npm install

# Build React app
npm run build

# Output: ./build directory
```

### 4.2 Deploy to Railway

```bash
# Create static service on Railway
railway add --name frontend

# Configure as static site
# Build command: npm run build
# Start command: (leave empty for static)
# Static path: ./build

# Deploy
railway up
```

### 4.3 Configure CORS

```bash
# Update backend CORS settings
# CORS_ORIGINS=https://your-frontend.railway.app

# Restart backend
railway restart
```

---

## Phase 5: SSL/TLS Configuration (Day 2)

### 5.1 Railway Auto SSL

```bash
# Railway automatically provisions SSL
# No additional configuration needed
# All traffic automatically redirected to HTTPS
```

### 5.2 Custom Domain (Optional)

```bash
# In Railway dashboard:
# 1. Go to project settings
# 2. Add custom domain
# 3. Update DNS records
# 4. SSL auto-provisioned via Let's Encrypt
```

---

## Phase 6: Monitoring Setup (Day 3)

### 6.1 Sentry Configuration

```bash
# Create Sentry account
# Visit: https://sentry.io

# Create new project (Python)
# Copy DSN to SENTRY_DSN

# Verify Sentry integration
# Deploy backend
# Trigger test error
# Check Sentry dashboard
```

### 6.2 Railway Monitoring

```bash
# In Railway dashboard:
# 1. View real-time metrics
# 2. CPU/Memory usage
# 3. Request latency
# 4. Error rates
# 5. Deployment history
```

### 6.3 Health Checks

```bash
# Endpoint: /health
# Frequency: Every 30 seconds
# Timeout: 10 seconds
# Failure threshold: 3 consecutive failures

# Configure in Railway:
# Settings → Health Checks
```

---

## Phase 7: Email System (Day 3)

### 7.1 SMTP Configuration

```bash
# Provide SMTP credentials:
# - SMTP_HOST
# - SMTP_PORT
# - SMTP_USERNAME
# - SMTP_PASSWORD
# - SMTP_FROM_EMAIL

# Update .env.production
railway variables set SMTP_HOST=your-smtp-host
railway variables set SMTP_PORT=587
# ... etc

# Restart backend
railway restart
```

### 7.2 Test Email

```bash
# Send test email
curl -X POST https://your-app.railway.app/api/test-email \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'
```

---

## Phase 8: Backup System (Day 3)

### 8.1 AWS S3 Setup

```bash
# Create S3 bucket
# Name: crucibai-backups
# Region: us-east-1
# Block public access: Yes

# Create IAM user for backups
# Permissions: s3:GetObject, s3:PutObject, s3:DeleteObject

# Get credentials
# AWS_ACCESS_KEY_ID
# AWS_SECRET_ACCESS_KEY

# Update environment variables
railway variables set AWS_ACCESS_KEY_ID=...
railway variables set AWS_SECRET_ACCESS_KEY=...
```

### 8.2 Schedule Backups

```bash
# Backups run daily at 2 AM UTC
# Retention: 30 days
# Verification: Automatic

# Monitor backups
# Endpoint: /api/admin/backups
# Check S3 bucket for backup files
```

### 8.3 Test Restore

```bash
# List backups
curl https://your-app.railway.app/api/admin/backups

# Restore from backup (requires admin)
curl -X POST https://your-app.railway.app/api/admin/restore \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"backup_filename": "daily-backups/full-2026-02-24T02:00:00.sql.gz"}'
```

---

## Phase 9: Rate Limiting (Day 4)

### 9.1 Configure Rate Limits

```bash
# Update environment variables
railway variables set RATE_LIMIT_WINDOW_MS=60000
railway variables set RATE_LIMIT_MAX_REQUESTS=100
railway variables set RATE_LIMIT_ANONYMOUS_MAX=10
railway variables set RATE_LIMIT_FREE_MAX=100
railway variables set RATE_LIMIT_PRO_MAX=1000
```

### 9.2 Test Rate Limiting

```bash
# Send 11 requests rapidly
for i in {1..11}; do
  curl https://your-app.railway.app/api/chat
done

# 11th request should return 429 (Too Many Requests)
```

---

## Phase 10: Admin Panel (Day 4)

### 10.1 Access Admin Panel

```bash
# URL: https://your-app.railway.app/admin
# Login with admin credentials
# Email: admin@crucibai.app
# Password: (set during first login)
```

### 10.2 Admin Features

- User management
- System analytics
- Billing & revenue
- System settings
- Backup management
- Alert monitoring

---

## Phase 11: Testing & Validation (Day 5)

### 11.1 Smoke Tests

```bash
# Test all critical endpoints
bash scripts/smoke-tests.sh

# Expected: All tests pass ✅
```

### 11.2 Load Testing

```bash
# Simulate production load
npm run test:load

# Expected: <2s average response time
```

### 11.3 Security Audit

```bash
# Run security checks
npm run test:security

# Expected: No critical vulnerabilities
```

---

## Phase 12: Go Live (Day 5)

### 12.1 Pre-Launch Checklist

- [ ] Database initialized and tested
- [ ] Backend deployed and healthy
- [ ] Frontend deployed and accessible
- [ ] SSL/TLS configured
- [ ] Monitoring active (Sentry + Railway)
- [ ] Email system configured
- [ ] Backups running
- [ ] Rate limiting active
- [ ] Admin panel accessible
- [ ] All smoke tests passing

### 12.2 Launch

```bash
# Announce availability
# Update DNS if using custom domain
# Monitor error rates for 24 hours
# Be ready to rollback if needed
```

### 12.3 Post-Launch Monitoring

```bash
# First 24 hours:
# - Check error rates every hour
# - Monitor CPU/memory usage
# - Verify backups completed
# - Test user registration flow
# - Test build generation

# First week:
# - Daily health checks
# - Weekly performance review
# - Monitor user feedback
```

---

## Rollback Procedure

If critical issues occur:

```bash
# 1. Identify issue
# 2. Check logs
railway logs --follow

# 3. Rollback to previous deployment
railway rollback

# 4. Verify health
curl https://your-app.railway.app/health

# 5. Investigate root cause
# 6. Fix and redeploy
```

---

## Monitoring & Maintenance

### Daily Tasks

```bash
# Check system health
curl https://your-app.railway.app/health

# Review error logs
# Visit Sentry dashboard

# Verify backups completed
# Check S3 bucket
```

### Weekly Tasks

```bash
# Review performance metrics
# Check user feedback
# Update dependencies (if needed)
# Review security alerts
```

### Monthly Tasks

```bash
# Performance optimization review
# Capacity planning
# Security audit
# Cost review
```

---

## Support & Troubleshooting

### Common Issues

**Database Connection Failed**
```bash
# Check DATABASE_URL
railway variables

# Verify connection
psql $DATABASE_URL

# Restart backend
railway restart
```

**High Error Rate**
```bash
# Check Sentry dashboard
# Review recent deployments
# Check logs
railway logs --follow

# Rollback if needed
railway rollback
```

**Slow Response Times**
```bash
# Check CPU/memory usage
# Review slow queries
# Scale up resources if needed
```

---

## Contact & Support

- **Documentation:** https://docs.crucibai.app
- **Status Page:** https://status.crucibai.app
- **Support Email:** support@crucibai.app
- **Emergency:** emergency@crucibai.app

---

**Deployment Guide Version:** 1.0
**Last Updated:** February 24, 2026
**Status:** Production Ready ✅
