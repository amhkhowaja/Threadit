#!/usr/bin/env bash
# Deploy or tear down the Threadit backend on REAL AWS (ALB + Fargate + DynamoDB
# + Cognito + OpenSearch + S3). The frontend is NOT deployed here — run it
# locally with `make app-aws`.
#
# Usage:
#   scripts/aws-deploy.sh up      # build+push image, create ECR if needed, apply
#   scripts/aws-deploy.sh down    # destroy the stack (stops billing)
#
# NOTE: this creates billable AWS resources (~$0.10-0.15/hr while up).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ACTION="${1:-}"
TF_DIR="$ROOT/terraform"
TF_STATE="prodweb.tfstate"
TFVARS="envs/awsbackend.tfvars"
REGION="${REGION:-eu-central-1}"
IMAGE_TAG="${IMAGE_TAG:-v1}"

for bin in terraform aws docker; do
  command -v "$bin" >/dev/null || { echo "ERROR: $bin not found on PATH"; exit 1; }
done

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
ECR_HOST="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"
REPO_NAME="threadit-prod-service"
IMAGE="${ECR_HOST}/${REPO_NAME}:${IMAGE_TAG}"

tf() { terraform -chdir="$TF_DIR" "$@"; }

case "$ACTION" in
  up)
    echo "==> terraform init"
    tf init -input=false >/dev/null

    echo "==> Ensuring ECR repo exists (needed before first image push)"
    aws ecr describe-repositories --repository-names "$REPO_NAME" --region "$REGION" >/dev/null 2>&1 \
      || aws ecr create-repository --repository-name "$REPO_NAME" --region "$REGION" >/dev/null

    echo "==> Building Lambda indexer package"
    make build-lambda >/dev/null

    echo "==> Building + pushing service image: $IMAGE"
    docker build -q -t "$IMAGE" . >/dev/null
    aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$ECR_HOST" >/dev/null
    docker push "$IMAGE" >/dev/null

    echo "==> terraform apply (state=$TF_STATE, vars=$TFVARS)"
    tf apply -input=false -auto-approve -state="$TF_STATE" -var-file="$TFVARS" -var "service_image=$IMAGE"

    echo
    echo "==> Deployed. Now run the frontend against it:  make app-aws"
    echo "    ALB: $(tf output -state="$TF_STATE" -raw alb_dns 2>/dev/null)"
    ;;

  down)
    echo "==> terraform destroy (state=$TF_STATE)"
    tf init -input=false >/dev/null
    tf destroy -input=false -auto-approve -state="$TF_STATE" -var-file="$TFVARS" -var "service_image=$IMAGE"
    echo "==> Stack destroyed. Billing stopped."
    ;;

  *)
    echo "Usage: $0 {up|down}"
    exit 1
    ;;
esac
