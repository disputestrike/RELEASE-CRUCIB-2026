# Agent Swarm Wiring

## PASS

- Complex multistack prompts now plan into the real `agents.*` DAG instead of `frontend.scaffold` / `backend.*` mini-pack phases.
- Helios-style enterprise prompts now plan into the same DAG swarm path.
- `agents.*` steps resolve to the new swarm executor bridge.
- Core swarm agents (`Planner`, `Requirements Clarifier`, `Stack Selector`, `Frontend Generation`, `Backend Generation`, `Database Agent`, `File Tool Agent`) now fail loudly if the server runtime returns `failed_with_fallback`, `failed`, or `skipped`.
- Auto-Runner checkpoints now keep the full step result payload so downstream DAG agents can read prior outputs.
- Proof log: `proof/agent_swarm_wiring/pytest_agent_swarm.log`
- Plan summary: `proof/agent_swarm_wiring/swarm_plan_summary.json`

## PASS METRICS

- AGENT_DAG nodes discovered: `123`
- DAG execution phases discovered: `8`
- Full multistack plan step count: `131`
- Helios enterprise plan step count: `131`
- `frontend.scaffold` present in swarm plans: `false`

## PARTIAL / ENVIRONMENT NOTE

- Two broader behavior-verification tests on this machine still fail because the local `DATABASE_URL` points at a PostgreSQL credential that does not authenticate (`password authentication failed for user "username"`). That is a local environment issue, not a regression from the swarm wiring patch.
