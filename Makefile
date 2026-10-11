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
	$(VENV)/bin/ruff check libs services tests
	$(VENV)/bin/lint-imports

.PHONY: fmt
fmt: ## Auto-format / auto-fix lint issues
	$(VENV)/bin/ruff check --fix libs services tests
	$(VENV)/bin/ruff format libs services tests

.PHONY: test
test: ## Run unit + api + contract tests (no AWS)
	$(PY) -m pytest tests/unit tests/api tests/contract -q

.PHONY: openapi
openapi: ## Regenerate the authoritative openapi/v1.json from the apps
	$(PY) tools/gen_openapi.py

.PHONY: check
check: lint test ## Lint + test (CI gate)

.PHONY: clean
clean: ## Remove caches
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache
