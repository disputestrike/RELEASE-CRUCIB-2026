# Root cause

- Enterprise prompts were being sent through the generic frontend/backend agent path first.
- When that path returned weak or empty output, CrucibAI silently downgraded to the generic preview scaffold.
- The generic scaffold rendered a sanitized slice of `job.goal`, which is why the published app showed the Aegis Omega spec instead of a real Helios product.

# Fix

- Enterprise prompt detection now routes directly into the enterprise command build pack before generic agents run.
- The enterprise pack emits a multi-page command center frontend, a tenant-aware FastAPI backend, and enterprise SQL migrations/seeds.
- The generic fallback no longer renders the raw prompt text into the visible app.
