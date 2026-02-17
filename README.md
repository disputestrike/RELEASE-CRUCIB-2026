# CrucibAI

**State the idea. We build it.** No product limit—web, SaaS, bots, agents, dashboards, tools. One idea to the next.

**Local app (after starting backend + frontend):**  
**http://localhost:3000**

Backend API: http://localhost:8000  

How to run: see **[RUN.md](RUN.md)**. Vision: **[BUILD_ANYTHING.md](BUILD_ANYTHING.md)**.

**Deploy / env:**  
- `RUN_IN_SANDBOX` — default `1`: runs (tests, security) use Docker when available; set `0` to disable.  
- `PREFER_LARGEST_MODEL` — set `1` or `true` to use the largest available model first for all agents.  
- After the main build DAG, a **bounded autonomy loop** runs once: it may re-run tests and security if they failed (self-heal).

**Value prop:** **[WHO_BUILDS_BETTER_FASTER_HELPFUL.md](WHO_BUILDS_BETTER_FASTER_HELPFUL.md)** — who builds better, faster, and more helpful for all users.

---

# Here are your Instructions
