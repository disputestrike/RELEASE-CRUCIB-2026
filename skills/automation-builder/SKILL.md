---
name: automation-builder
description: Build scheduled automations, webhook-triggered workflows, and AI-powered agents that run on a schedule or in response to events. Use when the user wants to automate a task, create a workflow, build an agent that runs daily, set up a webhook pipeline, or connect services together. Triggers on phrases like "automate X", "run this every day", "create an agent that", "build a workflow", "trigger this when", "send X to Y on schedule".
metadata:
  version: '1.0'
  category: automate
  icon: ⚡
  color: '#f97316'
---

# Automation Builder

## When to Use This Skill

Apply this skill when the user wants to automate a process or create a recurring workflow:

- "Automate my daily digest"
- "Create an agent that checks X every morning"
- "Build a workflow that triggers when Y happens"
- "Send a Slack message every day with Z"
- "Scrape this site and email me the results"
- Any request for a schedule, webhook, pipeline, or recurring task

## What This Skill Builds

Production-ready automation workflows:

**Automation Types**

1. **Scheduled Agent** — runs on a cron schedule
   - Daily digest (news, analytics, sales data)
   - Weekly report generator
   - Periodic data sync or scrape
   - Morning briefing to Slack/email

2. **Webhook Trigger** — runs when an event fires
   - New lead → enrich → CRM create → Slack notify
   - GitHub PR → AI code review → post comment
   - Stripe payment → send custom invoice → update sheet
   - Form submission → validate → notify + log

3. **Chained Pipeline** — sequential or parallel steps
   - Step 1: Fetch data → Step 2: Transform with AI → Step 3: Store → Step 4: Notify
   - Parallel branches that merge at the end

4. **AI-Powered Agent** — uses LLM to reason and act
   - Research agent (web search + summarize + email)
   - Lead finder (search LinkedIn/web + draft outreach)
   - Content refresher (update stale content with current data)
   - Inbox summarizer (read emails + categorize + reply drafts)

**Backend Components**
- Cron scheduler (`node-cron` or Railway cron jobs)
- Webhook receiver endpoint with signature validation
- Step runner with retry logic and error handling
- State persistence (track run history, last run time)
- Notification dispatch (Slack, email, webhook)
- Secrets management for API keys

**Monitoring UI**
- Automation list with last run time + status
- Run history log (success/fail + output preview)
- Enable/disable toggle
- Manual trigger button
- Error detail and retry

## Instructions

1. **Parse the automation** — identify: trigger type (schedule/webhook/manual), steps (fetch/transform/store/notify), integrations needed, failure behavior

2. **Define the data flow** — draw out: Input → Steps → Output → Where result goes

3. **Build in 3 passes**:
   - Pass 1: Config + types + DB schema (automations, runs, steps)
   - Pass 2: Core automation logic (step runner, retry, logging)
   - Pass 3: UI dashboard + API routes + scheduling setup

4. **Reliability rules**:
   - Every automation has retry: 3 attempts with exponential backoff
   - Every run logged with: start_time, end_time, status, output_preview, error
   - Dead letter queue for permanently failed runs
   - Idempotency keys for webhook handlers (never process twice)

5. **For AI-powered steps**:
   - Use structured output (JSON mode) when extracting data
   - Always include fallback if LLM returns unexpected format
   - Log token usage per run

6. **For scheduled runs**:
   - Use UTC cron expressions
   - Show next run time in user's local timezone

## Example Input → Output

Input: "Every morning at 8am, search for news about my competitors (Lovable, Bolt, Replit), summarize the key items with AI, and post to our #product Slack channel"

Output includes:
- Cron job: `0 8 * * *` (8am UTC)
- Step 1: Search for each competitor news (Tavily API)
- Step 2: AI summarization with Claude (structured JSON output)
- Step 3: Format as Slack blocks message
- Step 4: POST to Slack webhook
- `/server/automations/competitor-digest.ts` — complete automation
- `/server/scheduler.ts` — cron setup
- UI: dashboard showing last run + preview of sent message
