# CrucibAI Incident Response Playbooks

**Date:** February 24, 2026  
**Version:** 1.0  
**Status:** PHASE 8 - INCIDENT RESPONSE  

---

## Table of Contents

1. [Incident Classification](#incident-classification)
2. [Playbook: Service Down](#playbook-service-down)
3. [Playbook: High Error Rate](#playbook-high-error-rate)
4. [Playbook: Database Failure](#playbook-database-failure)
5. [Playbook: Memory Leak](#playbook-memory-leak)
6. [Playbook: Security Incident](#playbook-security-incident)
7. [Playbook: Data Loss](#playbook-data-loss)
8. [Communication Templates](#communication-templates)
9. [Post-Incident Review](#post-incident-review)

---

## Incident Classification

### Severity Levels

| Level | Response Time | Example | Page On-Call |
|-------|---------------|---------|--------------|
| **P1 - Critical** | 15 minutes | Service completely down, data loss | YES |
| **P2 - High** | 1 hour | 50%+ error rate, performance degradation | YES |
| **P3 - Medium** | 4 hours | 10-50% error rate, partial outage | NO |
| **P4 - Low** | 24 hours | Minor bugs, non-critical features | NO |

### Incident Commander Role

The first person to detect an incident becomes the **Incident Commander** until explicitly handed off.

**Responsibilities:**
- Declare incident severity
- Coordinate response team
- Communicate status updates
- Document all actions
- Schedule post-incident review

---

## Playbook: Service Down

**Severity:** P1 - Critical  
**Response Time:** 15 minutes  
**On-Call:** YES

### Symptoms

- API returns 503 Service Unavailable
- All endpoints timing out
- Zero successful requests for 5+ minutes
- Monitoring alerts triggered

### Initial Response (0-5 minutes)

**1. Declare Incident**
```bash
# Notify team
slack: @on-call-team "P1: Service Down - Starting incident response"

# Create incident channel
slack: /incident create service-down
```

**2. Check Status Dashboard**
```bash
# Access monitoring
- Datadog: https://app.datadoghq.com/dashboard
- AWS CloudWatch: https://console.aws.amazon.com/cloudwatch
- Application logs: tail -f /var/log/crucibai/app.log
```

**3. Determine Root Cause**
```bash
# Check API server status
curl -v http://localhost:3000/health

# Check database connectivity
psql $DATABASE_URL -c "SELECT 1"

# Check external dependencies
curl -v https://api.manus.im/health

# Check system resources
top -b -n 1 | head -20
df -h
free -h
```

### Investigation (5-15 minutes)

**Check Recent Changes**
```bash
# View recent deployments
git log --oneline -10

# Check CI/CD status
# GitHub Actions: https://github.com/disputestrike/CrucibAI/actions

# View recent config changes
git diff HEAD~1 .env
```

**Analyze Logs**
```bash
# Search for errors
grep -i "error\|fatal\|panic" /var/log/crucibai/app.log | tail -50

# Search for specific patterns
grep "connection refused" /var/log/crucibai/app.log
grep "out of memory" /var/log/crucibai/app.log
grep "timeout" /var/log/crucibai/app.log
```

**Check Dependencies**
```bash
# Database
psql $DATABASE_URL -c "SELECT version();"

# Redis (if used)
redis-cli ping

# External APIs
curl -I https://api.manus.im

# S3
aws s3 ls --region us-east-1
```

### Recovery (15-30 minutes)

**Option 1: Restart Service**
```bash
# If service is hung or crashed
systemctl restart crucibai-api

# Verify service is running
systemctl status crucibai-api
curl http://localhost:3000/health
```

**Option 2: Rollback Deployment**
```bash
# If recent deployment caused issue
git log --oneline -5
git revert <commit-hash>
git push origin main

# Monitor deployment
# GitHub Actions: https://github.com/disputestrike/CrucibAI/actions
```

**Option 3: Scale Up**
```bash
# If under load
# Railway: https://railway.app/project/...
# Increase instance count or upgrade tier

# Monitor metrics
watch -n 5 'curl http://localhost:3000/metrics'
```

**Option 4: Failover**
```bash
# If primary database is down
# Switch to read replica
# Update DATABASE_URL environment variable
# Restart service

# Verify failover
psql $DATABASE_URL -c "SELECT 1;"
```

### Communication

**Initial Status (within 5 minutes)**
```
🚨 INCIDENT: Service Down (P1)
Status: Investigating
Impact: All users unable to access API
ETA: 15 minutes
```

**Update (every 5 minutes)**
```
🔍 INCIDENT UPDATE: Service Down
Status: Found root cause (database connection pool exhausted)
Action: Restarting service
ETA: 5 minutes
```

**Resolution**
```
✅ RESOLVED: Service Down
Duration: 12 minutes
Root Cause: Database connection pool exhausted due to connection leak
Fix: Restarted service and deployed connection pool fix
Post-Incident Review: Scheduled for tomorrow
```

### Verification

- [ ] API responding to requests
- [ ] Error rate < 1%
- [ ] Response time < 500ms
- [ ] Database queries completing
- [ ] External dependencies accessible
- [ ] Monitoring alerts cleared

---

## Playbook: High Error Rate

**Severity:** P2 - High  
**Response Time:** 1 hour  
**On-Call:** YES

### Symptoms

- Error rate > 10%
- 5xx errors in logs
- User complaints in support channel
- Monitoring alert triggered

### Initial Response (0-10 minutes)

**1. Declare Incident**
```bash
slack: @on-call-team "P2: High Error Rate - Starting investigation"
```

**2. Identify Error Pattern**
```bash
# Count errors by type
grep "ERROR\|FATAL" /var/log/crucibai/app.log | tail -100 | \
  awk '{print $NF}' | sort | uniq -c | sort -rn

# Find most common error
grep "500" /var/log/crucibai/app.log | head -20

# Check error rate over time
tail -1000 /var/log/crucibai/app.log | \
  grep -c "ERROR\|FATAL" | awk '{print $1/10 "%"}'
```

**3. Check Affected Endpoints**
```bash
# Identify which endpoints are failing
grep "POST\|GET\|PUT\|DELETE" /var/log/crucibai/app.log | \
  grep "500" | awk '{print $7}' | sort | uniq -c | sort -rn

# Test affected endpoints
curl -v http://localhost:3000/api/build
curl -v http://localhost:3000/api/agents
```

### Investigation (10-30 minutes)

**Check Resource Usage**
```bash
# CPU usage
top -b -n 1 | head -15

# Memory usage
free -h
ps aux | grep crucibai | grep -v grep

# Disk usage
df -h
du -sh /var/log/crucibai/

# Network connections
netstat -an | grep ESTABLISHED | wc -l
```

**Check Recent Changes**
```bash
# Recent commits
git log --oneline -10 --since="1 hour ago"

# Recent deployments
# Check GitHub Actions or deployment logs

# Recent config changes
git diff HEAD~1 server/
```

**Check Dependencies**
```bash
# Database performance
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity;"

# Slow queries
psql $DATABASE_URL -c "SELECT query, calls, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"

# Redis memory
redis-cli INFO memory

# External API status
curl -I https://api.manus.im
```

### Recovery (30-60 minutes)

**Option 1: Fix Bad Code**
```bash
# If recent commit caused issue
git log --oneline -5
git show <commit-hash>
git revert <commit-hash>
git push origin main
```

**Option 2: Optimize Slow Query**
```bash
# Identify slow query
psql $DATABASE_URL -c "EXPLAIN ANALYZE SELECT ..."

# Add index if needed
psql $DATABASE_URL -c "CREATE INDEX idx_name ON table(column);"

# Restart service
systemctl restart crucibai-api
```

**Option 3: Increase Resources**
```bash
# Scale up on Railway
# Increase instance count or upgrade tier

# Monitor improvement
watch -n 5 'curl http://localhost:3000/metrics | grep error_rate'
```

**Option 4: Disable Feature**
```bash
# If specific feature causing errors
# Set feature flag to disable it
export FEATURE_NEW_AGENT_SYSTEM=false
systemctl restart crucibai-api
```

### Verification

- [ ] Error rate < 1%
- [ ] No 5xx errors in logs
- [ ] All endpoints responding
- [ ] Response time < 500ms
- [ ] Database queries fast
- [ ] Resource usage normal

---

## Playbook: Database Failure

**Severity:** P1 - Critical  
**Response Time:** 15 minutes  
**On-Call:** YES

### Symptoms

- Database connection refused
- "Connection timeout" errors
- Slow queries (>5s)
- Database CPU at 100%

### Initial Response (0-5 minutes)

**1. Verify Database Status**
```bash
# Try to connect
psql $DATABASE_URL -c "SELECT 1;"

# Check connection status
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity;"

# Check for locks
psql $DATABASE_URL -c "SELECT * FROM pg_locks WHERE NOT granted;"
```

**2. Check Database Metrics**
```bash
# Railway dashboard
# https://railway.app/project/...

# AWS RDS dashboard
# https://console.aws.amazon.com/rds/

# Check CPU, memory, connections
```

### Investigation (5-15 minutes)

**Identify Problem**
```bash
# Long-running queries
psql $DATABASE_URL -c "SELECT pid, usename, query, query_start FROM pg_stat_activity WHERE state != 'idle' ORDER BY query_start;"

# Locks
psql $DATABASE_URL -c "SELECT * FROM pg_locks WHERE NOT granted;"

# Connection count
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity;"

# Database size
psql $DATABASE_URL -c "SELECT pg_size_pretty(pg_database_size(current_database()));"
```

### Recovery (15-30 minutes)

**Option 1: Kill Long-Running Query**
```bash
# Identify query
psql $DATABASE_URL -c "SELECT pid, query FROM pg_stat_activity WHERE query_start < now() - interval '5 minutes';"

# Kill it
psql $DATABASE_URL -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE pid = 12345;"
```

**Option 2: Restart Database**
```bash
# Railway: Use dashboard to restart
# AWS RDS: Use console to reboot

# Verify connectivity
psql $DATABASE_URL -c "SELECT 1;"
```

**Option 3: Failover to Replica**
```bash
# If primary is down
# Promote read replica
# Update DATABASE_URL

# Verify failover
psql $DATABASE_URL -c "SELECT 1;"
```

**Option 4: Scale Database**
```bash
# If out of connections
# Increase max_connections parameter
# Upgrade instance size

# Restart database
```

### Verification

- [ ] Database responding to queries
- [ ] Connection count < max_connections
- [ ] No long-running queries
- [ ] No locks
- [ ] Response time < 100ms
- [ ] API can connect

---

## Playbook: Memory Leak

**Severity:** P2 - High  
**Response Time:** 1 hour  
**On-Call:** YES

### Symptoms

- Memory usage grows over time
- OOM (Out of Memory) errors
- Service crashes
- Slow response times

### Initial Response (0-10 minutes)

**1. Check Memory Usage**
```bash
# Current memory
free -h
ps aux | grep crucibai | grep -v grep

# Memory over time
watch -n 5 free -h

# Process memory
ps -eo pid,vsz,rss,comm | grep crucibai
```

**2. Identify Memory Leak**
```bash
# Check if memory grows with requests
# Send 100 requests
for i in {1..100}; do curl http://localhost:3000/api/build; done

# Check memory again
free -h
ps aux | grep crucibai | grep -v grep
```

### Investigation (10-30 minutes)

**Analyze Memory Usage**
```bash
# Memory by process
ps aux | sort -k6 -rn | head -10

# Memory by module
python3 -m memory_profiler script.py

# Check for memory leaks in code
grep -r "global " backend/ | grep -v test
grep -r "cache\[" backend/ | grep -v test
```

**Check Logs**
```bash
# Look for patterns
grep -i "memory\|leak\|cache" /var/log/crucibai/app.log

# Check for large allocations
grep "allocated\|buffer\|array" /var/log/crucibai/app.log
```

### Recovery (30-60 minutes)

**Option 1: Restart Service**
```bash
# Temporary fix
systemctl restart crucibai-api

# Monitor memory
watch -n 5 'ps aux | grep crucibai'
```

**Option 2: Fix Memory Leak**
```bash
# Identify leak in code
# Common causes:
# - Unbounded caches
# - Circular references
# - Event listener not removed
# - Large objects not freed

# Example fix:
# Before:
cache = {}  # Unbounded

# After:
from functools import lru_cache
@lru_cache(maxsize=1000)
def expensive_function():
    pass
```

**Option 3: Increase Memory**
```bash
# Temporary: Scale up on Railway
# Permanent: Fix the leak

# Monitor improvement
watch -n 5 'free -h'
```

### Verification

- [ ] Memory stable over time
- [ ] No OOM errors
- [ ] Service not crashing
- [ ] Response time normal
- [ ] Memory < 80% of limit

---

## Playbook: Security Incident

**Severity:** P1 - Critical  
**Response Time:** 15 minutes  
**On-Call:** YES

### Symptoms

- Unauthorized access detected
- Data breach suspected
- Malicious activity in logs
- Security alert triggered

### Initial Response (0-5 minutes)

**1. Declare Incident**
```bash
slack: @security-team @on-call-team "P1: Security Incident - Immediate response required"
```

**2. Isolate System**
```bash
# If compromised:
# - Revoke all API keys
# - Disable user accounts if needed
# - Isolate affected systems

# Do NOT:
# - Delete logs
# - Shut down systems (preserve evidence)
# - Communicate publicly
```

**3. Gather Evidence**
```bash
# Preserve logs
cp -r /var/log/crucibai /var/log/crucibai-incident-backup

# Check for unauthorized access
grep "unauthorized\|forbidden\|denied" /var/log/crucibai/app.log

# Check for data access
grep "SELECT\|UPDATE\|DELETE" /var/log/crucibai/app.log | grep -v "FROM pg_"
```

### Investigation (5-30 minutes)

**Identify Attack Vector**
```bash
# Check access logs
tail -1000 /var/log/crucibai/access.log | grep -v "200\|304"

# Check for suspicious IPs
awk '{print $1}' /var/log/crucibai/access.log | sort | uniq -c | sort -rn | head -20

# Check for brute force attempts
grep "401\|403" /var/log/crucibai/access.log | awk '{print $1}' | sort | uniq -c | sort -rn

# Check for SQL injection attempts
grep "'; DROP\|union select\|or 1=1" /var/log/crucibai/app.log
```

**Determine Scope**
```bash
# What data was accessed?
grep "SELECT" /var/log/crucibai/app.log | grep -v "FROM pg_"

# What was modified?
grep "UPDATE\|DELETE\|INSERT" /var/log/crucibai/app.log

# Which users were affected?
grep "user_id" /var/log/crucibai/app.log | awk '{print $NF}' | sort | uniq
```

### Recovery (30-60 minutes)

**Option 1: Revoke Compromised Credentials**
```bash
# Rotate API keys
# Update all services using old keys

# Reset passwords for affected users
# Send notification emails

# Revoke sessions
# Force re-authentication
```

**Option 2: Patch Vulnerability**
```bash
# If SQL injection:
# - Use parameterized queries
# - Validate input
# - Add WAF rules

# If auth bypass:
# - Fix auth logic
# - Add additional checks
# - Increase logging

# Deploy patch
git commit -m "Security fix: [vulnerability]"
git push origin main
```

**Option 3: Restore from Backup**
```bash
# If data was modified
# Restore from clean backup
# Verify data integrity

# Restore database
pg_restore -d $DATABASE_URL /backups/crucibai-clean.dump

# Verify
psql $DATABASE_URL -c "SELECT count(*) FROM users;"
```

### Communication

**Internal (Immediate)**
```
🚨 SECURITY INCIDENT: Unauthorized Access Detected
Severity: P1 - Critical
Impact: [Describe impact]
Action: [Describe action taken]
Status: Investigating

DO NOT:
- Post on social media
- Contact customers yet
- Delete logs
```

**External (After Investigation)**
```
We have detected and contained a security incident.
- What happened: [Brief description]
- When: [Date/time]
- Impact: [Who was affected]
- What we did: [Actions taken]
- What you should do: [Customer actions]
```

### Verification

- [ ] Threat contained
- [ ] Compromised credentials revoked
- [ ] Vulnerability patched
- [ ] Data integrity verified
- [ ] Monitoring enhanced
- [ ] Post-incident review scheduled

---

## Playbook: Data Loss

**Severity:** P1 - Critical  
**Response Time:** 15 minutes  
**On-Call:** YES

### Symptoms

- Data missing from database
- Accidental deletion
- Backup corruption
- Data inconsistency

### Initial Response (0-5 minutes)

**1. Stop All Writes**
```bash
# Prevent further data loss
# Set database to read-only if possible
psql $DATABASE_URL -c "ALTER DATABASE crucibai SET default_transaction_read_only = on;"

# Or restart with read-only flag
systemctl stop crucibai-api
```

**2. Assess Damage**
```bash
# Check what's missing
psql $DATABASE_URL -c "SELECT count(*) FROM users;"
psql $DATABASE_URL -c "SELECT count(*) FROM builds;"

# Check for recent changes
psql $DATABASE_URL -c "SELECT * FROM pg_stat_statements ORDER BY query_start DESC LIMIT 10;"
```

### Investigation (5-15 minutes)

**Identify Cause**
```bash
# Check for DELETE statements
grep "DELETE" /var/log/crucibai/app.log | tail -20

# Check for DROP statements
grep "DROP" /var/log/crucibai/app.log

# Check for truncate
grep "TRUNCATE" /var/log/crucibai/app.log

# Check audit logs
grep "user_id\|admin" /var/log/crucibai/app.log | grep -i "delete\|drop"
```

### Recovery (15-30 minutes)

**Option 1: Restore from Backup**
```bash
# Find latest clean backup
ls -lh /backups/

# Restore to point-in-time
pg_restore -d crucibai-restored /backups/crucibai-2026-02-24-10:00.dump

# Verify data
psql -d crucibai-restored -c "SELECT count(*) FROM users;"

# If good, switch over
# Update DATABASE_URL to point to restored database
```

**Option 2: Restore Deleted Rows**
```bash
# If using WAL (Write-Ahead Logging)
# Can recover to point-in-time before deletion

# Stop database
systemctl stop postgresql

# Restore from backup and replay WAL
pg_basebackup -D /var/lib/postgresql/data-restored
pg_wal_replay -t "2026-02-24 10:00:00"

# Start database
systemctl start postgresql
```

### Verification

- [ ] Data restored
- [ ] Data integrity verified
- [ ] No data loss
- [ ] Backups working
- [ ] Monitoring alerts cleared

---

## Communication Templates

### Incident Declared

```
🚨 INCIDENT: [Service] [Issue]
Severity: P[1-4]
Status: Investigating
Impact: [Who/what affected]
ETA: [Estimated resolution time]

We are aware of the issue and working on it.
More updates in 5 minutes.
```

### Status Update

```
🔍 INCIDENT UPDATE: [Service] [Issue]
Status: [Investigating/Identified/Fixing/Recovering]
Root Cause: [If identified]
Action: [What we're doing]
ETA: [New estimate]

Thank you for your patience.
```

### Incident Resolved

```
✅ RESOLVED: [Service] [Issue]
Duration: [Total time]
Root Cause: [What happened]
Fix: [What we did]
Impact: [Affected users/data]

We apologize for the disruption.
Post-incident review coming tomorrow.
```

---

## Post-Incident Review

### Schedule

- **P1:** Within 24 hours
- **P2:** Within 48 hours
- **P3:** Within 1 week
- **P4:** As needed

### Attendees

- Incident Commander
- On-call engineer
- Engineering lead
- Product manager (if user-facing)

### Agenda

**1. Timeline (15 minutes)**
- When incident started
- When detected
- When resolved
- Key actions taken

**2. Root Cause Analysis (20 minutes)**
- What caused the incident
- Why it wasn't caught earlier
- Contributing factors

**3. Impact Assessment (10 minutes)**
- How many users affected
- How long affected
- Data loss or corruption
- Financial impact

**4. Action Items (15 minutes)**
- What we'll do to prevent recurrence
- Who's responsible
- When it will be done
- How we'll verify

**5. Lessons Learned (10 minutes)**
- What went well
- What could be better
- Process improvements

### Action Items Template

```
ACTION ITEM: [Description]
Owner: [Name]
Due Date: [Date]
Priority: [P1/P2/P3]
Status: [Not Started/In Progress/Done]

Example:
ACTION ITEM: Add database query timeout to prevent hanging queries
Owner: Alice
Due Date: 2026-02-28
Priority: P1
Status: Not Started
```

---

## References

- [NIST Incident Response Guide](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-61r2.pdf)
- [AWS Incident Response](https://aws.amazon.com/incident-response/)
- [Google SRE Book - Incident Response](https://sre.google/books/)

---

**Prepared by:** Manus AI  
**Last Updated:** February 24, 2026  
**Next Review:** March 24, 2026  
**Version:** 1.0
