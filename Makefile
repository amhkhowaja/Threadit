# Threadit — build & developer tasks.
# Incremental: lint + test now; infra/build/deploy targets added as phases land.

.DEFAULT_GOAL := help

VENV        := .venv
PY          := $(VENV)/bin/python
PIP         := $(VENV)/bin/pip
CORE_PATH   := libs/threadit_core
export PYTHONPATH := $(CORE_PATH):.

.PHONY: help
help: ## List available targets
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

$(VENV): ## Create the virtualenv
	python3 -m venv $(VENV)

.PHONY: install
install: $(VENV) ## Install runtime + dev dependencies
	$(PIP) install -q --upgrade pip
	$(PIP) install -q \
		fastapi==0.115.5 pydantic==2.9.2 pydantic-settings==2.6.1 \
		boto3==1.35.54 structlog==24.4.0 "pyjwt[crypto]==2.9.0" \
		"uvicorn[standard]==0.32.0" \
		pytest==8.3.3 pytest-asyncio==0.24.0 pytest-cov==6.0.0 \
		httpx==0.27.2 ruff==0.7.2 import-linter==2.1

.PHONY: lint
lint: ## Run ruff + the no-boto3-past-repository-boundary contract (R5)
	$(VENV)/bin/ruff check libs services tools tests
	$(VENV)/bin/lint-imports

.PHONY: fmt
fmt: ## Auto-format / auto-fix lint issues
	$(VENV)/bin/ruff check --fix libs services tools tests
	$(VENV)/bin/ruff format libs services tools tests

.PHONY: test
test: ## Run unit + api + contract tests (no AWS)
	$(PY) -m pytest tests/unit tests/api tests/contract -q

.PHONY: openapi
openapi: ## Regenerate the authoritative openapi/v1.json from the apps
	$(PY) tools/gen_openapi.py

.PHONY: build-lambda
build-lambda: ## Assemble the indexer Lambda package (handler + core + deps)
	rm -rf build/lambda && mkdir -p build/lambda/services/indexer
	cp -r libs/threadit_core/threadit_core build/lambda/threadit_core
	cp services/indexer/handler.py services/indexer/__init__.py build/lambda/services/indexer/
	touch build/lambda/services/__init__.py
	$(PIP) install -q --target build/lambda urllib3==2.2.3 structlog==24.4.0

.PHONY: build-loadgen
build-loadgen: ## Assemble the in-VPC loadgen Lambda package
	rm -rf build/loadgen && mkdir -p build/loadgen/services/loadgen
	cp services/loadgen/handler.py services/loadgen/__init__.py build/loadgen/services/loadgen/
	touch build/loadgen/services/__init__.py

.PHONY: check
check: lint test ## Lint + test (CI gate)

# ---------------------------------------------------------------------------
# App launch — run the FULL app (frontend + backend) with one command.
# ---------------------------------------------------------------------------

.PHONY: setup
setup: ## One-command contributor setup (venv, deps, frontend, browsers)
	./scripts/setup.sh

.PHONY: app-floci
app-floci: ## Run the full app locally on Floci (no AWS) -> http://localhost:5173
	./scripts/run-floci.sh

.PHONY: app-aws
app-aws: ## Run the local frontend against the deployed AWS backend -> http://localhost:5173
	./scripts/run-aws.sh

.PHONY: app-stop
app-stop: ## Stop locally-launched app processes (frontend + backend services)
	./scripts/stop.sh

.PHONY: aws-up
aws-up: ## Deploy the backend to REAL AWS (builds+pushes image; billing!)
	./scripts/aws-deploy.sh up

.PHONY: aws-down
aws-down: ## Tear down the AWS backend stack (stops billing)
	./scripts/aws-deploy.sh down

.PHONY: seed
seed: ## Seed a clean local Floci Threadit with real forum content (needs app-floci)
	./scripts/seed/run.sh

.PHONY: floci-up
floci-up: ## Start the pinned Floci emulator (dev AWS)
	docker compose up -d

.PHONY: floci-down
floci-down: ## Stop Floci
	docker compose down

.PHONY: itest
itest: ## Integration tests against Floci (requires floci-up)
	AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test \
	THREADIT_AWS_ENDPOINT_URL=http://localhost:4566 \
	$(PY) -m pytest tests/integration -q

TF_DIR := terraform
ENV ?= dev

.PHONY: tf-plan
tf-plan: ## terraform plan (ENV=dev|prod)
	cd $(TF_DIR) && terraform init -input=false >/dev/null && \
	terraform plan -input=false -var-file=envs/$(ENV).tfvars

.PHONY: tf-apply
tf-apply: ## terraform apply (ENV=dev=Floci | prod=real AWS)
	cd $(TF_DIR) && terraform init -input=false >/dev/null && \
	terraform apply -input=false -auto-approve -var-file=envs/$(ENV).tfvars

.PHONY: tf-destroy
tf-destroy: ## terraform destroy (ENV=dev|prod)
	cd $(TF_DIR) && terraform destroy -input=false -auto-approve -var-file=envs/$(ENV).tfvars

.PHONY: smoke
smoke: ## End-to-end smoke against the Floci-provisioned stack (requires tf-apply ENV=dev)
	AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test \
	THREADIT_AWS_ENDPOINT_URL=http://localhost:4566 \
	$(PY) tools/smoke.py

.PHONY: nfr
nfr: ## Multi-user NFR/load suite (set backend env first: Floci or AWS)
	$(PY) -m tests.load.run_nfr

.PHONY: clean
clean: ## Remove caches
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache
