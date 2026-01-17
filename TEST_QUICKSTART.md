# Testing Quick Start for Claude Code Users

Get up and running with the test suite in 2 minutes!

## 🚀 Quick Setup

```bash
# 1. Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Navigate to mcp-server directory
cd mcp-with-proper-enterprise-auth/mcp-server

# 3. Install dependencies with uv (fast!)
uv sync --extra dev

# 4. Run tests to verify everything works
make test
```

## 🎯 Recommended Workflow for Claude Code

### Option 1: Watch Mode (Best for Active Development)

**Open two terminals:**

Terminal 1 - Start watch mode:
```bash
cd mcp-with-proper-enterprise-auth/mcp-server
make watch
```

Terminal 2 - Edit code:
```bash
# Edit files in app/ or tests/
# Tests auto-run when you save!
```

**Benefits:**
- ✅ Instant feedback on code changes
- ✅ See test results without switching windows
- ✅ Catches errors immediately
- ✅ Red/green feedback loop

### Option 2: Quick Runs (Best for Check-ins)

```bash
# Before committing, run quick tests
make quick

# Or full test suite
make test

# Or full CI checks
make ci
```

## 📊 Most Useful Commands

```bash
# Run all tests (verbose)
make test

# Watch mode - auto-run on changes
make watch

# Quick run - fast feedback
make quick

# Unit tests only (very fast)
make test-unit

# Integration tests
make test-integration

# With coverage report
make test-cov
make cov-report  # Opens HTML report

# Run only failed tests from last run
make test-failed

# Full CI simulation
make ci
```

## 🏃 Running Specific Tests

```bash
# By marker
pytest -m jwt          # JWT tests only
pytest -m dcr          # DCR tests only
pytest -m unit         # Unit tests only
pytest -m integration  # Integration tests only

# By file
pytest tests/test_jwt_validator.py

# By specific test
pytest tests/test_jwt_validator.py::TestJWTValidator::test_validate_token_with_valid_user_token

# With verbose output
pytest -vv

# Stop on first failure
pytest -x

# Show print statements
pytest -s
```

## 🎨 Understanding Test Output

### Success ✅
```
tests/test_config.py::TestSettings::test_settings_from_env PASSED     [ 10%]
tests/test_config.py::TestSettings::test_entra_authority_property PASSED [ 20%]
...
================================ 25 passed in 2.35s ================================
```

### Failure ❌
```
tests/test_jwt_validator.py::TestJWTValidator::test_validate_token FAILED [50%]
________________________________ FAILURES _______________________________________
...
AssertionError: Expected X but got Y
```

### Watch Mode 👀
```
========================================
MCP Server Test Watch Mode
========================================

Running tests with args: -v --tb=short --maxfail=1

Watching for changes...
Clear: True
[CHANGES DETECTED] Running tests...
```

## 🔍 Debugging Failed Tests

If a test fails:

1. **Read the error message** - It usually tells you what's wrong
2. **Run with verbose output**:
   ```bash
   pytest -vv tests/test_that_failed.py
   ```

3. **Add print statements** or use debugger:
   ```python
   def test_something():
       result = my_function()
       print(f"DEBUG: result = {result}")  # Will show with -s flag
       assert result == expected
   ```

4. **Run with debugger**:
   ```bash
   pytest --pdb  # Drops into debugger on failure
   ```

## 📈 Coverage Reports

```bash
# Generate coverage report
make test-cov

# Open HTML report in browser
make cov-report

# Or manually
open htmlcov/index.html
```

Coverage reports show:
- ✅ Which lines are tested (green)
- ❌ Which lines are not tested (red)
- 📊 Coverage percentage per file

## ✍️ Writing Your Own Tests

### 1. Create test file
```bash
touch tests/test_my_feature.py
```

### 2. Write test
```python
import pytest

@pytest.mark.unit
def test_my_feature():
    """Test that my feature works."""
    # Arrange
    input_data = "test"

    # Act
    result = my_function(input_data)

    # Assert
    assert result == "expected"
```

### 3. Run it
```bash
pytest tests/test_my_feature.py
```

### 4. Use fixtures
```python
def test_with_fixture(valid_user_token):
    """Use existing fixture from conftest.py"""
    # valid_user_token is automatically provided
    assert len(valid_user_token) > 0
```

## 🎓 Learning Resources

1. **Start here**: `tests/README.md` - Comprehensive testing guide
2. **See examples**: Look at existing test files in `tests/`
3. **Fixtures**: Check `tests/conftest.py` for available fixtures
4. **Pytest docs**: https://docs.pytest.org/

## ⚡ Pro Tips

1. **Keep watch mode running** while you code - instant feedback!
2. **Use `make quick`** for fast check before commits
3. **Run `make ci`** before pushing to catch CI failures locally
4. **Mark slow tests** with `@pytest.mark.slow` to skip them in quick runs
5. **Use fixtures** - Don't repeat setup code
6. **Test one thing per test** - Makes failures easier to debug

## 🐛 Common Issues

### "ModuleNotFoundError: No module named 'app'"

**Solution**: Run pytest from the `mcp-server` directory:
```bash
cd mcp-with-proper-enterprise-auth/mcp-server
pytest
```

### "pytest: command not found"

**Solution**: Install dependencies:
```bash
pip install -r requirements.txt
```

### Watch mode not working

**Solution**: Install pytest-watch:
```bash
pip install pytest-watch
chmod +x scripts/test-watch.sh
```

### Tests running but all skip/fail

**Solution**: Check environment variables are set in `tests/conftest.py`

## 🎯 Your First Test Run

Try this right now:

```bash
# 1. Go to mcp-server directory
cd mcp-with-proper-enterprise-auth/mcp-server

# 2. Run a single test file
pytest tests/test_config.py -v

# 3. If that works, run all tests
pytest

# 4. If all pass, try watch mode!
make watch
```

Expected output:
```
========================= test session starts ==========================
collected 15 items

tests/test_config.py::TestSettings::test_settings_from_env PASSED  [  6%]
tests/test_config.py::TestSettings::test_entra_authority_property PASSED [ 13%]
...
========================= 15 passed in 1.23s ===========================
```

## 🚀 Next Steps

1. **Run tests now** - Make sure everything works
2. **Start watch mode** - Try the recommended workflow
3. **Read tests/README.md** - Learn more about the test suite
4. **Write a test** - Practice with a simple test
5. **Check coverage** - See what's already tested

---

**Happy Testing! 🎉**

The test suite is here to help you code with confidence. Use it!
