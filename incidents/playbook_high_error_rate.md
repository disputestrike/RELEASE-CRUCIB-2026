# Incident Playbook: High Error Rate

## Detection Criteria

- Error rate exceeds 5% for more than 5 minutes
- CloudWatch alarm `crucibai-high-error-rate` triggers
- Slack notification in #incidents channel

## Severity Levels

- **Critical:** >20% error rate
- **High:** 10-20% error rate
- **Medium:** 5-10% error rate

## Immediate Actions (0-5 minutes)

1. **Acknowledge the incident**
   - Respond to Slack alert
   - Create incident ticket in Jira
   - Notify on-call engineer

2. **Gather initial data**
   - Check CloudWatch dashboard
   - Review recent deployments
   - Check application logs for error patterns

3. **Assess impact**
   - How many users affected?
   - Which features are impacted?
   - Is data integrity at risk?

## Investigation Steps (5-15 minutes)

1. **Identify error type**
   ```bash
   # Query logs for error patterns
   aws logs filter-log-events \
     --log-group-name /crucibai/app/prod \
     --filter-pattern "ERROR" \
     --start-time $(date -d '10 minutes ago' +%s)000
   ```

2. **Check recent changes**
   - Review git log for recent commits
   - Check deployment history
   - Review configuration changes

3. **Examine agent logs**
   - Check which agents are failing
   - Look for timeout patterns
   - Check resource constraints

4. **Check dependencies**
   - Database connectivity
   - S3 availability
   - External API status
   - Redis/cache status

## Resolution Steps (15-30 minutes)

### If caused by recent deployment:
```bash
# Rollback to previous version
railway rollback --service backend --version <previous-version>
```

### If caused by database issue:
```bash
# Check database connections
psql -h $DB_HOST -U $DB_USER -c "SELECT count(*) FROM pg_stat_activity;"

# Kill long-running queries if needed
psql -h $DB_HOST -U $DB_USER -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE duration > interval '5 minutes';"
```

### If caused by agent failure:
```bash
# Restart agent service
railway restart --service agents
```

### If caused by resource exhaustion:
```bash
# Check memory usage
free -h

# Check disk space
df -h

# Scale up if needed
railway scale --service backend --memory 2G
```

## Post-Incident (30+ minutes)

1. **Verify resolution**
   - Monitor error rate for 10 minutes
   - Confirm users can access features
   - Check no data corruption occurred

2. **Document findings**
   - Root cause
   - Timeline of events
   - Actions taken
   - Impact assessment

3. **Create follow-up tasks**
   - Fix underlying issue
   - Add monitoring/alerting
   - Update runbooks
   - Schedule post-mortem

## Escalation

- If unresolved after 15 minutes → escalate to engineering lead
- If unresolved after 30 minutes → escalate to CTO
- If data loss suspected → escalate to security team

## Related Playbooks

- [Database Down](./playbook_database_down.md)
- [Agent Failure](./playbook_agent_failure.md)
- [Memory Leak](./playbook_memory_leak.md)

## Contacts

- On-call Engineer: Slack @oncall
- Engineering Lead: @eng-lead
- CTO: @cto
