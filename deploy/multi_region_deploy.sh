#!/usr/bin/env bash
# Multi-region deploy helper — STUB: requires AWS_ACCOUNT, ECR repos, Terraform backends.
set -euo pipefail

ENV="${1:-prod}"
REGIONS="${2:-us-east-1,us-west-2,eu-west-1}"

echo "[multi_region_deploy] environment=$ENV regions=$REGIONS"
echo "[multi_region_deploy] Set AWS_ACCOUNT and ensure ECR repos exist before pushing images."

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AWS_ACCOUNT="${AWS_ACCOUNT:-}"

if [[ -z "$AWS_ACCOUNT" ]]; then
  echo "[multi_region_deploy] AWS_ACCOUNT not set — skipping docker login/push (stub OK for CI docs)."
  exit 0
fi

if [[ -f "$ROOT/backend/Dockerfile" ]]; then
  docker build -t crucibai-api:latest -f "$ROOT/backend/Dockerfile" "$ROOT"
else
  echo "[multi_region_deploy] backend/Dockerfile missing — skip API image"
fi

if [[ -f "$ROOT/frontend/Dockerfile" ]]; then
  docker build -t crucibai-web:latest -f "$ROOT/frontend/Dockerfile" "$ROOT"
else
  echo "[multi_region_deploy] frontend/Dockerfile missing — skip web image"
fi

IFS=',' read -r -a REGION_ARRAY <<< "$REGIONS"
for region in "${REGION_ARRAY[@]}"; do
  region="$(echo "$region" | xargs)"
  [[ -z "$region" ]] && continue
  aws ecr get-login-password --region "$region" | docker login --username AWS --password-stdin \
    "${AWS_ACCOUNT}.dkr.ecr.${region}.amazonaws.com"
  docker tag crucibai-api:latest "${AWS_ACCOUNT}.dkr.ecr.${region}.amazonaws.com/crucibai-api:latest" || true
  docker push "${AWS_ACCOUNT}.dkr.ecr.${region}.amazonaws.com/crucibai-api:latest" || true
done

TF_DIR="$ROOT/infra/multi_region/aws"
if [[ -d "$TF_DIR" ]]; then
  (cd "$TF_DIR" && terraform init -input=false && terraform apply -var="environment=$ENV" -auto-approve)
else
  echo "[multi_region_deploy] $TF_DIR not found"
fi
