# Multi-region deployment stubs (CrucibAI)

Educational **scaffolding only** — not production-ready VPC, IAM, RDS Global, or replication.

- `variables.tf` — shared inputs for examples below.
- `aws/` — minimal AWS provider + outputs; extend with Aurora Global, Route53, ECR, etc.
- `gcp/` — minimal Google provider stub; extend with Cloud SQL HA + replicas.
- `azure/` — minimal AzureRM stub; extend with paired regions + Front Door.

Run `terraform fmt` / `validate` after you add backends, credentials, and real modules.

_Schema: crucibai.infra.multi_region/v1_
