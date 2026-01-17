# UV Setup Guide

This project uses [uv](https://github.com/astral-sh/uv) for fast Python package and environment management.

## Why uv?

- **⚡ 10-100x faster** than pip
- **🔒 Reliable** - Reproducible installs with lockfile
- **🎯 Simple** - No virtual env activation needed
- **🔄 Compatible** - Works with existing Python tools
- **📦 Modern** - Built in Rust, designed for speed

## Quick Start

### 1. Install uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# With pip (if you prefer)
pip install uv

# With Homebrew
brew install uv
```

### 2. Set up the project

```bash
cd mcp-with-proper-enterprise-auth/mcp-server

# Install all dependencies (fast!)
uv sync --extra dev

# That's it! No virtual env activation needed.
```

### 3. Run tests

```bash
# Run tests with uv
uv run pytest

# Or use make commands (recommended)
make test
make watch
```

## How uv Works

### Automatic Environment Management

uv automatically creates and manages a `.venv` directory for you:

```bash
# uv creates .venv on first sync
uv sync

# Run commands in the uv environment
uv run pytest              # Run tests
uv run python app/main.py  # Run app
uv run black app           # Format code
```

**No need to activate the virtual environment!** `uv run` handles it for you.

### Dependency Management

```bash
# Install dependencies from pyproject.toml
uv sync

# Install with dev dependencies
uv sync --extra dev

# Install with AWS extras
uv sync --extra aws

# Install all extras
uv sync --all-extras

# Update dependencies
uv sync --upgrade

# Add a new dependency
uv add requests

# Add a dev dependency
uv add --dev pytest-mock

# Remove a dependency
uv remove requests
```

### Lockfile

uv creates a `uv.lock` file that ensures reproducible installs:

```bash
# Update lockfile
uv lock

# Install from lockfile (exact versions)
uv sync
```

**Commit `uv.lock` to version control** for reproducible builds!

## Using uv with the MCP Server

### Development Workflow

```bash
cd mcp-server

# 1. Install dependencies (once)
uv sync --extra dev

# 2. Run tests in watch mode
make watch
# or
uv run ./scripts/test-watch.sh

# 3. Run the server
make run
# or
uv run python -m uvicorn app.main:app --reload
```

### Running Tests

```bash
# Quick test run
make test
# or
uv run pytest

# Watch mode (auto-rerun on changes)
make watch

# Specific test markers
uv run pytest -m unit
uv run pytest -m integration
uv run pytest -m jwt

# With coverage
make test-cov
# or
uv run pytest --cov=app --cov-report=html
```

### Code Quality

```bash
# Format code
make format
# or
uv run black app tests
uv run isort app tests

# Lint code
make lint
# or
uv run flake8 app tests
uv run mypy app

# All CI checks
make ci
```

## Makefile Commands (All use uv)

All make commands automatically use uv:

```bash
make help          # Show all commands
make setup         # Complete project setup
make install       # Install all dependencies
make install-dev   # Install dev dependencies
make test          # Run tests
make watch         # Watch mode
make test-cov      # Tests with coverage
make lint          # Run linters
make format        # Format code
make run           # Run dev server
make ci            # Full CI checks
```

## Comparing uv to pip/venv

### Old way (pip + venv):
```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
pip install -r requirements-dev.txt
pytest
deactivate
```

### New way (uv):
```bash
uv sync --extra dev
uv run pytest
```

Much simpler and **much faster**!

## uv in CI/CD

The project's GitHub Actions workflow uses uv:

```yaml
- name: Install uv
  uses: astral-sh/setup-uv@v4

- name: Install dependencies
  run: uv sync --extra dev

- name: Run tests
  run: uv run pytest
```

Benefits:
- **Faster CI builds** (cached uv environment)
- **Reproducible** (uses uv.lock)
- **Reliable** (same environment locally and in CI)

## uv in Docker

The Dockerfile can optionally use uv for faster builds:

```dockerfile
# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install dependencies (fast!)
RUN uv sync --no-dev
```

## Advanced Usage

### Python Version Management

```bash
# Install a specific Python version
uv python install 3.11

# Use a specific Python version
uv python pin 3.11

# List installed Python versions
uv python list
```

### Dependency Tree

```bash
# Show dependency tree
uv tree

# Show why a package is installed
uv tree --package requests
```

### Cache Management

```bash
# Show cache directory
uv cache dir

# Show cache size
uv cache prune --dry-run

# Clean cache
uv cache clean
```

### Export requirements.txt

If you need a requirements.txt file:

```bash
# Export dependencies
uv pip compile pyproject.toml -o requirements.txt

# Or use make command
make uv-export
```

## Troubleshooting

### "uv: command not found"

Install uv:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc  # or restart shell
```

### Dependencies not found

Sync dependencies:
```bash
cd mcp-server
uv sync --extra dev
```

### Wrong Python version

Pin the correct version:
```bash
uv python install 3.11
uv python pin 3.11
uv sync
```

### Import errors when running tests

Make sure you're using `uv run`:
```bash
# Don't do this:
pytest

# Do this:
uv run pytest
# or
make test
```

### Clean start

```bash
# Remove everything and start fresh
make clean-all    # Removes .venv and cache
uv sync --extra dev
```

## Migration from pip

If you have an existing virtual environment:

```bash
# Deactivate old venv
deactivate

# Remove old venv
rm -rf venv

# Install with uv
uv sync --extra dev

# Done! Now use `uv run` or make commands
```

## Best Practices

1. **Commit `uv.lock`** - Ensures reproducible builds
2. **Use `uv run`** - No need to activate environments
3. **Use make commands** - They handle uv for you
4. **Run `uv sync`** - After pulling changes
5. **Use `--extra dev`** - For development dependencies

## Resources

- [uv Documentation](https://docs.astral.sh/uv/)
- [uv GitHub](https://github.com/astral-sh/uv)
- [uv Discord](https://discord.gg/astral-sh)

## Summary

**With uv, you get:**
- ✅ Faster installs (10-100x speedup)
- ✅ Simpler workflow (`uv run` instead of activation)
- ✅ Reproducible builds (uv.lock)
- ✅ Better caching
- ✅ Modern tooling

**To get started:**
```bash
# 1. Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Set up project
cd mcp-server && make setup

# 3. Run tests
make test
```

That's it! 🚀
