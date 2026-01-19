.PHONY: help test test-unit test-integration test-cov clean install

help:
	@echo "MCP Client Tests - Available Commands:"
	@echo ""
	@echo "  make install           Install test dependencies"
	@echo "  make test              Run all tests"
	@echo "  make test-unit         Run unit tests only (fast)"
	@echo "  make test-integration  Run integration tests only"
	@echo "  make test-cov          Run tests with coverage"
	@echo "  make test-verbose      Run tests with verbose output"
	@echo "  make test-failed       Re-run only failed tests"
	@echo "  make cov-report        Open HTML coverage report"
	@echo "  make clean             Clean test artifacts"
	@echo ""

install:
	@echo "Installing test dependencies..."
	pip install -r requirements.txt

test:
	@echo "Running all tests..."
	pytest -v

test-unit:
	@echo "Running unit tests..."
	pytest -v -m unit

test-integration:
	@echo "Running integration tests..."
	pytest -v -m integration

test-cov:
	@echo "Running tests with coverage..."
	pytest --cov=. --cov-report=term-missing --cov-report=html

test-verbose:
	@echo "Running tests with verbose output..."
	pytest -vv -s

test-failed:
	@echo "Re-running failed tests..."
	pytest --lf -v

cov-report:
	@echo "Opening coverage report..."
	open htmlcov/index.html || xdg-open htmlcov/index.html || echo "Open htmlcov/index.html in your browser"

clean:
	@echo "Cleaning test artifacts..."
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf __pycache__
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "Clean complete"
