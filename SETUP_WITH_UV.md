# Complete Setup Guide with uv

This guide walks you through setting up the MCP server using uv for blazing-fast Python environment management.

## Why This Guide?

This project now uses **uv** instead of traditional pip/venv because:
- ⚡ **10-100x faster** installs
- 🔒 **Reproducible** builds with lockfile
- 🎯 **Simpler** workflow (no venv activation)
- 🚀 **Better for CI/CD** (faster, more reliable)

## Complete Setup (First Time)

### Step 1: Install uv

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows:**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Verify installation:**
```bash
uv --version
# Should output: uv 0.x.x
```

### Step 2: Clone and Configure

```bash
# Clone repository (if not already done)
git clone <repo-url>
cd mcp-with-proper-enterprise-auth

# Copy environment file
cp .env.example .env

# Edit .env with your Entra ID configuration
# (You'll need to create app registrations first - see docs/setup/entra-id-setup.md)
nano .env  # or vim, code, etc.
```

### Step 3: Install Dependencies

```bash
cd mcp-server

# Install all dependencies with dev tools
# This is FAST (usually < 5 seconds!)
uv sync --extra dev
```

What this does:
- Downloads all dependencies
- Creates `.venv` directory automatically
- Installs dev tools (pytest, black, mypy, etc.)
- Creates/updates `uv.lock` for reproducibility

### Step 4: Verify Installation

```bash
# Run tests to verify everything works
make test

# Should see output like:
# ✓ 100+ tests passing
# ✓ Coverage report
```

### Step 5: Start Developing!

**Option A: Watch Mode (Recommended for Claude Code)**

```bash
# Terminal 1: Start watch mode
make watch

# Terminal 2: Edit code
# Tests auto-run when you save!
```

**Option B: Run Server**

```bash
# Start development server
make run

# Server starts at http://localhost:8000
# API docs at http://localhost:8000/docs
```

## Daily Workflow

### Starting Your Day

```bash
cd mcp-with-proper-enterprise-auth/mcp-server

# Pull latest changes
git pull

# Sync dependencies (in case dependencies changed)
uv sync --extra dev

# Start watch mode for development
make watch
```

### Running Tests

```bash
# All tests
make test

# Watch mode (auto-rerun on changes)
make watch

# Only unit tests (fast)
make test-unit

# With coverage
make test-cov

# Specific test file
uv run pytest tests/test_jwt_validator.py

# Specific test
uv run pytest tests/test_jwt_validator.py::TestJWTValidator::test_validate_token
```

### Running the Server

```bash
# Development mode (auto-reload)
make run

# Or directly
uv run python -m uvicorn app.main:app --reload
```

### Code Quality

```bash
# Format code
make format

# Check formatting
make format-check

# Run linters
make lint

# Type checking
make typecheck

# All CI checks
make ci
```

### Adding Dependencies

```bash
# Add a runtime dependency
uv add <package-name>

# Add a dev dependency
uv add --dev <package-name>

# Examples:
uv add requests
uv add --dev pytest-mock

# Dependencies are auto-added to pyproject.toml
# and uv.lock is updated
```

## Common Commands

### Most Used

```bash
make help          # Show all available commands
make setup         # Complete first-time setup
make test          # Run all tests
make watch         # Watch mode (recommended!)
make run           # Run dev server
make ci            # Full CI checks before commit
```

### All Commands

```bash
# Testing
make test          # All tests
make test-unit     # Unit tests only
make test-integration  # Integration tests
make test-cov      # With coverage
make watch         # Watch mode
make quick         # Fast feedback

# Code Quality
make lint          # Run linters
make format        # Format code
make typecheck     # Type check

# Development
make run           # Dev server
make shell         # Python shell with app loaded

# Dependencies
make sync          # Sync dependencies
make deps-update   # Update all dependencies
make deps-tree     # Show dependency tree

# Cleanup
make clean         # Clean generated files
make clean-all     # Clean including uv cache
```

## Using uv Directly

Sometimes you want to use uv commands directly:

```bash
# Run any Python command in the uv environment
uv run <command>

# Examples:
uv run pytest
uv run python app/main.py
uv run black app
uv run mypy app

# Python REPL with all dependencies
uv run python

# Install dependencies
uv sync
uv sync --extra dev
uv sync --all-extras

# Add/remove packages
uv add requests
uv add --dev pytest-mock
uv remove requests

# Show dependency tree
uv tree

# Update lockfile
uv lock

# Update all dependencies
uv sync --upgrade
```

## No Virtual Environment Activation!

**Old way (pip + venv):**
```bash
python -m venv venv
source venv/bin/activate  # Every time!
pip install -r requirements.txt
pytest
deactivate
```text

**New way (uv):**
```bash
uv sync --extra dev
uv run pytest  # No activation needed!
```

uv automatically uses the `.venv` directory for you!

## Troubleshooting

### "uv: command not found"

uv isn't installed or not in PATH.

**Solution:**
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Restart terminal or source profile
source ~/.bashrc
# or
source ~/.zshrc
```

### "No such file or directory: 'pytest'"

You're trying to run pytest without `uv run`.

**Solution:**
```bash
# Don't do this:
pytest

# Do this:
uv run pytest

# Or use make (recommended):
make test
```

### Dependencies not found

Dependencies not installed or out of sync.

**Solution:**
```bash
cd mcp-server
uv sync --extra dev
```

### Import errors

PYTHONPATH issues or not using uv environment.

**Solution:**
```bash
# Always use `uv run` for Python commands
uv run pytest
uv run python app/main.py

# Or use make commands
make test
make run
```

### Clean start

Something is broken, start fresh.

**Solution:**
```bash
# Remove everything
make clean-all

# Reinstall
uv sync --extra dev

# Verify
make test
```

### Wrong Python version

Using wrong Python version.

**Solution:**
```bash
# Check current version
python --version

# Install Python 3.11 with uv
uv python install 3.11

# Pin to 3.11
uv python pin 3.11

# Sync dependencies
uv sync --extra dev
```

## IDE Setup

### VS Code

Add to `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/mcp-server/.venv/bin/python",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestPath": "${workspaceFolder}/mcp-server/.venv/bin/pytest",
  "python.formatting.provider": "black",
  "python.formatting.blackPath": "${workspaceFolder}/mcp-server/.venv/bin/black",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.mypyEnabled": true
}
```

### PyCharm

1. File → Settings → Project → Python Interpreter
2. Click gear icon → Add
3. Select "Existing environment"
4. Choose `mcp-server/.venv/bin/python`

## CI/CD

GitHub Actions automatically uses uv:

```yaml
- name: Install uv
  uses: astral-sh/setup-uv@v4

- name: Install dependencies
  run: uv sync --extra dev

- name: Run tests
  run: uv run pytest
```

Benefits:
- ✅ Faster builds (~3x speedup)
- ✅ Reproducible (uses uv.lock)
- ✅ Better caching

## Docker

Docker can optionally use uv for faster builds:

```dockerfile
# Add uv to Docker image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install dependencies (fast!)
RUN uv sync --no-dev
```

## Best Practices

1. **Always commit `uv.lock`**
   - Ensures reproducible builds
   - Same dependencies for all developers
   - Required for CI/CD

2. **Use `make` commands**
   - They handle uv for you
   - Consistent across team
   - Documented with `make help`

3. **Run `uv sync` after pulling**
   - Keep dependencies up to date
   - Fast (uses lockfile)

4. **Use `uv run` for Python commands**
   - No need to activate venv
   - Always uses correct environment

5. **Use watch mode during development**
   - Instant feedback
   - Auto-runs tests
   - `make watch`

## Next Steps

### For New Developers

1. Read this guide
2. Install uv
3. Run `make setup`
4. Run `make watch`
5. Start coding!

### For Testing

1. Read [TEST_QUICKSTART.md](./TEST_QUICKSTART.md)
2. Run `make watch`
3. Edit code, tests auto-run!

### For Deployment

1. Read deployment guides in `docs/setup/`
2. Docker Compose: Already configured
3. AWS Fargate: See `docs/setup/fargate-deployment.md`
4. Agent Core: See `docs/setup/agentcore-deployment.md`

## Resources

- **[UV_SETUP.md](./UV_SETUP.md)** - Complete uv guide
- **[TEST_QUICKSTART.md](./TEST_QUICKSTART.md)** - Testing guide
- **[QUICKSTART.md](./QUICKSTART.md)** - General quick start
- **[uv Documentation](https://docs.astral.sh/uv/)** - Official uv docs
- **`make help`** - All available commands

## Summary

**With uv, you get:**
- ✅ Faster everything (10-100x speedup)
- ✅ Simpler workflow (no venv activation)
- ✅ Reproducible builds (lockfile)
- ✅ Better tooling (modern, Rust-based)

**Your workflow:**
```bash
# 1. Install uv (once)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Set up project (once per clone)
cd mcp-server && make setup

# 3. Daily development
make watch  # Auto-run tests on changes

# 4. Before commit
make ci     # Run all checks
```

**That's it! Happy coding! 🚀**
