# Makefile for MCP Server development and testing
# Uses uv for fast Python package and environment management

.PHONY: help install test test-unit test-integration test-security test-watch test-cov clean lint format docker-build docker-run

# Default target
.DEFAULT_GOAL := help

# Colors
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m # No Color

# Detect uv
UV := $(shell command -v uv 2> /dev/null)

help: ## Show this help message
	@echo "$(GREEN)MCP Server - Available Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

check-uv: ## Check if uv is installed
ifndef UV
	@echo "$(YELLOW)uv is not installed. Installing uv...$(NC)"
	@curl -LsSf https://astral.sh/uv/install.sh | sh
	@echo "$(GREEN)✓ uv installed. Please restart your shell or run: source ~/.bashrc$(NC)"
	@exit 1
else
	@echo "$(GREEN)✓ uv is installed$(NC)"
endif

sync: check-uv ## Sync dependencies with uv (fast)
	uv sync

install: check-uv ## Install all dependencies with uv
	uv sync --all-extras

install-dev: check-uv ## Install with development dependencies
	uv sync --extra dev

test: check-uv ## Run all tests
	uv run pytest

test-unit: check-uv ## Run unit tests only
	uv run pytest -m unit

test-integration: check-uv ## Run integration tests only
	uv run pytest -m integration

test-security: check-uv ## Run security tests only
	uv run pytest -m security

test-jwt: check-uv ## Run JWT-related tests only
	uv run pytest -m jwt

test-dcr: check-uv ## Run DCR-related tests only
	uv run pytest -m dcr

test-auth: check-uv ## Run auth-related tests only
	uv run pytest -m auth

test-api: check-uv ## Run API endpoint tests only
	uv run pytest -m api

test-watch: check-uv ## Run tests in watch mode (auto-rerun on changes)
	@chmod +x scripts/test-watch.sh
	uv run ./scripts/test-watch.sh

test-watch-unit: check-uv ## Watch mode for unit tests only
	@chmod +x scripts/test-watch.sh
	uv run ./scripts/test-watch.sh -m unit

test-cov: check-uv ## Run tests with coverage report
	uv run pytest --cov=app --cov-report=html --cov-report=term-missing

test-cov-unit: check-uv ## Run unit tests with coverage
	uv run pytest -m unit --cov=app --cov-report=html --cov-report=term-missing

test-verbose: check-uv ## Run tests with verbose output
	uv run pytest -vv -s

test-fast: check-uv ## Run tests with minimal output (fast feedback)
	uv run pytest -q --tb=line

test-failed: check-uv ## Re-run only failed tests from last run
	uv run pytest --lf

test-debug: check-uv ## Run tests with debugging output
	uv run pytest -vv -s --log-cli-level=DEBUG

clean: ## Clean up generated files
	rm -rf __pycache__ .pytest_cache .mypy_cache htmlcov .coverage coverage.xml
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage" -delete
	rm -rf .uv

clean-all: clean ## Clean everything including uv cache
	uv cache clean

lint: check-uv ## Run linters (flake8, mypy)
	uv run flake8 app tests --max-line-length=100
	uv run mypy app

format: check-uv ## Format code with black and isort
	uv run black app tests
	uv run isort app tests

format-check: check-uv ## Check if code is formatted correctly
	uv run black --check app tests
	uv run isort --check app tests

typecheck: check-uv ## Run type checking with mypy
	uv run mypy app

docker-build: ## Build Docker image
	docker build -t mcp-server:latest .

docker-run: ## Run Docker container
	docker run -p 8000:8000 --env-file ../.env mcp-server:latest

docker-test: ## Run tests in Docker
	docker-compose -f ../docker-compose.yml run --rm mcp-server uv run pytest

run: check-uv ## Run development server
	uv run python -m uvicorn app.main:app --reload --port 8000

run-prod: check-uv ## Run production server
	uv run python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# CI/CD targets
ci-test: clean check-uv ## Run tests for CI/CD
	uv run pytest --junitxml=junit/test-results.xml --cov=app --cov-report=xml --cov-report=html

ci-lint: check-uv ## Run linters for CI/CD
	uv run flake8 app tests --max-line-length=100 --format=default
	uv run mypy app

ci-format-check: check-uv ## Check formatting for CI/CD
	uv run black --check app tests
	uv run isort --check app tests

ci: clean ci-lint ci-format-check ci-test ## Run all CI checks

# Database/Redis (if needed)
redis-start: ## Start Redis in Docker (for token revocation)
	docker-compose -f ../docker-compose.yml up -d redis

redis-stop: ## Stop Redis
	docker-compose -f ../docker-compose.yml stop redis

# Utility targets
shell: check-uv ## Open Python shell with app context
	uv run python -c "from app.config import get_settings; from app.main import create_app; settings = get_settings(); app = create_app(); print('Settings and app loaded. Use settings and app variables.')" -i

deps-update: check-uv ## Update dependencies
	uv sync --upgrade

deps-tree: check-uv ## Show dependency tree
	uv tree

uv-lock: check-uv ## Update uv.lock file
	uv lock

cov-report: ## Open coverage report in browser
	open htmlcov/index.html || xdg-open htmlcov/index.html

# Documentation
docs-serve: check-uv ## Serve API documentation (Swagger UI)
	@echo "$(GREEN)Starting server on http://localhost:8000/docs$(NC)"
	uv run python -m uvicorn app.main:app --reload --port 8000

# Quick feedback loop for Claude Code
quick: clean test-fast ## Quick test run (fast, minimal output)
	@echo "$(GREEN)✓ Quick tests passed!$(NC)"

watch: test-watch ## Alias for test-watch

# All tests with coverage
full: clean test-cov ## Run full test suite with coverage
	@echo "$(GREEN)✓ Full test suite completed!$(NC)"
	@echo "$(YELLOW)Coverage report: htmlcov/index.html$(NC)"

# Setup target for first-time setup
setup: check-uv install-dev ## Complete project setup with uv
	@echo "$(GREEN)✓ Project setup complete!$(NC)"
	@echo "$(YELLOW)Run 'make test' to verify everything works$(NC)"
