---
name: internal-tool-builder
description: Build internal admin tools, back-office dashboards, CRUD interfaces, approval workflows, and operations software for teams. Use when the user wants to build a tool for their own team, internal admin panel, ops dashboard, data management interface, or any back-office application. Triggers on phrases like "build an admin panel", "create an internal tool", "I need a dashboard for my team", "build a CRUD interface", "create an approval workflow".
metadata:
  version: '1.0'
  category: build
  icon: 🛠️
  color: '#64748b'
---

# Internal Tool Builder

## When to Use This Skill

Apply this skill when building software for internal team use:

- "Build an admin panel for managing X"
- "Create a dashboard my team can use to Y"
- "I need a CRUD interface for our Z data"
- "Build an approval workflow for requests"
- "Create an operations dashboard"
- Any request for an internal tool, back-office app, or team dashboard

## What This Skill Builds

A production-ready internal tool:

**Data Tables**
- Sortable, filterable, paginated data tables
- Column visibility toggle
- Bulk select and bulk actions (delete, export, update status)
- Inline editing (click cell to edit)
- Row expand with detail view
- CSV/Excel export

**Forms & Input**
- Multi-step forms with validation (Zod)
- Dynamic forms (add/remove rows)
- File upload with preview
- Rich text editor (for notes/descriptions)
- Date range pickers
- Search with autocomplete

**Approval Workflows**
- Request submission by team members
- Manager review queue with approve/reject + notes
- Multi-level approval chains
- Notification on status change (email/Slack)
- Audit trail of all approvals

**Access Control**
- Role-based views (what each role can see/do)
- Action permissions (who can delete, who can approve)
- User management by admins
- Login via email (no OAuth required for internal)

**Integrations**
- Connect to existing databases or APIs
- Import/export CSV
- Slack notifications on key events
- Email digests (daily summary)
- Webhook triggers for downstream systems

**Dashboard Metrics**
- KPI cards (count, sum, average)
- Trend charts (daily/weekly/monthly)
- Status distribution (pie/donut charts)
- Recent activity feed

## Instructions

1. **Define the tool's purpose** — what data does it manage, who uses it (roles), what actions do they take, what needs approval

2. **Design the data model** — list entities, their fields, and relationships

3. **Build in 4 passes**:
   - Pass 1: Config + DB schema + types + auth setup
   - Pass 2: Data tables + forms for primary entity
   - Pass 3: Secondary entities + approval workflow + notifications
   - Pass 4: Dashboard metrics + admin user management + README

4. **Table quality rules**:
   - Every table has: search, column sort, status filter, pagination (25/50/100 per page)
   - Export to CSV must work for every table
   - Empty states have helpful messages (not just "No data")
   - Loading skeletons instead of spinners

5. **Form quality rules**:
   - All fields validated on submit
   - Inline error messages under each field
   - Success toast on save
   - Confirm dialog for destructive actions

6. **Approval workflow rules**:
   - Each request has: created_by, status (pending/approved/rejected/cancelled), reviewed_by, review_notes, timestamps
   - Approvers see all pending in their queue sorted by oldest first
   - Email notification to requester on decision

## Example Input → Output

Input: "Build an internal tool for managing contractor invoices — contractors submit invoices, finance team reviews and approves them, then marks them as paid"

Output includes:
- `/src/pages/Invoices.tsx` — table of all invoices with filters (pending, approved, paid)
- `/src/pages/SubmitInvoice.tsx` — contractor submission form
- `/src/pages/ReviewQueue.tsx` — finance team approval queue
- `/src/pages/Dashboard.tsx` — monthly spend, pending count, overdue alerts
- `/server/routes/invoices.ts` — CRUD + approval state machine
- `/database/schema.sql` — invoices, line_items, approvals, users tables
- Email templates for submission confirmation and approval notification
