# Admin: How to Access, When to Use It, What’s in It

## How do I access the admin?

- **From the app footer:** When you’re logged in and on any app page (e.g. Dashboard, Workspace), the footer has an **Admin** link. Click it to go to **Admin Dashboard**.
- **Direct URL:** `/app/admin` (e.g. `https://your-app.up.railway.app/app/admin`).
- **Who can see it:** The link is in the footer for everyone. If your account is **not** an admin, opening `/app/admin` will redirect you back to the main app. Only users with **admin role** (or listed in the backend’s admin list) can use the admin section.

**To make yourself an admin:** Your backend has a list of admin user IDs (or an `admin_role` on the user). Set your user’s `admin_role` in the database, or add your user ID to the admin list in the backend config (e.g. `ADMIN_USER_IDS` in `server.py`), then log in again.

---

## When do I need to access the admin?

Use the admin when you need to:

- See how the product is doing (signups, revenue, usage).
- Look up or manage users (credits, roles, support).
- Check analytics (daily/weekly reports, exports).
- Handle billing or support (e.g. grant credits, view user profile).

You don’t need it for normal use (building projects, using the workspace, buying tokens). It’s for **you as the operator** of CrucibAI.

---

## What’s in the admin? (What we have)

| Section | What it does |
|--------|------------------|
| **Dashboard** (`/app/admin`) | Overview: total users, signups today/this week, referrals, projects today, revenue (today / 7d / 30d), fraud flags count, system health. |
| **Users** (`/app/admin/users`) | List users (search by email, filter by plan). Open a user to see profile and grant credits. |
| **User profile** (`/app/admin/users/:id`) | One user: details, credits, grant-credits action. |
| **Billing** (`/app/admin/billing`) | Billing-related admin (payments, plans). |
| **Analytics** (`/app/admin/analytics`) | Daily/weekly metrics, date ranges, CSV export. |
| **Legal** (`/app/admin/legal`) | Legal/admin content as needed. |

All of this uses the same backend and database as the rest of the app; there is no separate “admin backend.”

---

## What do typical companies have in the admin?

Typical admin panels include:

- **Dashboard** — Key numbers (users, revenue, signups, errors). ✅ We have this.
- **User management** — List users, search, view profile, edit (e.g. credits, role, suspend). ✅ We have list + profile + grant credits.
- **Analytics / reports** — Usage over time, revenue, exports (CSV). ✅ We have daily/weekly and CSV.
- **Billing / payments** — Refunds, payment history, plan changes. ✅ We have a Billing section.
- **Support / moderation** — Tickets, abuse flags, content moderation. We have a placeholder for fraud flags; you can extend as needed.
- **Settings / config** — Feature flags, pricing, email templates. You can add these later if you need them.

So: **we have the usual core (dashboard, users, analytics, billing).** The footer Admin link is there so you can get to it quickly; only admins can actually use the pages.
