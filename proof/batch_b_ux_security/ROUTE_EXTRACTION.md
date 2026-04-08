# Batch B Route Extraction

## Before

- Public trust endpoints lived inside backend/server.py near the job trust-report routes.
- Proof lookup assumed a repo layout and did not cleanly model the Docker image path.

## After

- backend/routes/trust.py owns:
  - GET /api/trust/benchmark-summary
  - GET /api/trust/security-posture
- backend/server.py registers the trust router near the final router-inclusion block.
- The extracted router checks local repo proof paths and Docker image proof paths, including /proof/benchmarks/repeatability_v1.

## Preserved Contract

- /api/trust/benchmark-summary still returns ready/not_available status, counts, thresholds, cases, and proof paths.
- /api/trust/security-posture still returns database, tenant isolation, terminal policy, proof locations, and generated-app publish route.
