# MCP Server Tests

Comprehensive test suite for the MCP server with proper enterprise authentication.

## Test Structure

```text
tests/
├── conftest.py              # Pytest fixtures and configuration
├── test_config.py           # Configuration module tests
├── test_jwks_cache.py       # JWKS caching tests
├── test_jwt_validator.py    # JWT validation tests
├── test_token_validator.py  # Token type detection and permission validation
├── test_dcr_detector.py     # DCR client detection tests
└── test_api.py              # API endpoint integration tests
```

## Test Categories (Markers)

Tests are organized using pytest markers:

- `@pytest.mark.unit` - Unit tests (fast, isolated)
- `@pytest.mark.integration` - Integration tests (may require external services)
- `@pytest.mark.security` - Security-related tests
- `@pytest.mark.jwt` - JWT validation tests
- `@pytest.mark.dcr` - DCR emulation tests
- `@pytest.mark.auth` - Authentication tests
- `@pytest.mark.api` - API endpoint tests
- `@pytest.mark.slow` - Slow tests (may take >1s)

## Running Tests

### Quick Start

```bash
# All tests
make test

# Unit tests only (fast)
make test-unit

# Integration tests
make test-integration

# Security tests
make test-security

# With coverage
make test-cov
```

### Using pytest directly

```bash
# All tests
pytest

# Specific marker
pytest -m unit
pytest -m jwt
pytest -m dcr

# Specific file
pytest tests/test_jwt_validator.py

# Specific test
pytest tests/test_jwt_validator.py::TestJWTValidator::test_validate_token_with_valid_user_token

# Verbose output
pytest -vv

# Show print statements
pytest -s

# Stop on first failure
pytest -x

# Run last failed tests
pytest --lf

# Run only failed tests from last run
pytest --ff
```

### Watch Mode (Auto-rerun on changes)

**Recommended for active development with Claude Code!**

```bash
# Watch all tests
make test-watch

# Watch unit tests only
make test-watch-unit

# Or directly
./scripts/test-watch.sh

# With custom args
./scripts/test-watch.sh -m jwt -v
```

The watch mode will:

- Auto-detect file changes
- Clear terminal on each run
- Show only relevant output
- Stop on first failure for quick feedback

### Coverage Reports

```bash
# Run tests with coverage
make test-cov

# Open HTML report in browser
make cov-report

# Coverage for specific marker
pytest -m unit --cov=app --cov-report=html
```

Coverage reports are generated in `htmlcov/` directory.

## Test Fixtures

### Settings & Configuration

- `test_settings` - Test settings loaded from environment
- `mock_settings` - Mock settings for isolated testing

### JWT & JWKS

- `private_key` / `public_key` - RSA key pair for JWT signing
- `jwks_response` - Mock JWKS response from Entra ID
- `user_jwt_claims` - Claims for user (delegated) token
- `app_only_jwt_claims` - Claims for app-only (service principal) token
- `expired_jwt_claims` - Expired JWT claims
- `create_jwt_token` - Factory fixture to create signed JWTs
- `valid_user_token` - Valid signed user token
- `valid_app_token` - Valid signed app-only token
- `expired_token` - Expired signed token

### Invalid Tokens (for testing error handling)

- `invalid_token` - Malformed JWT
- `token_without_kid` - JWT without kid header
- `token_wrong_issuer` - JWT with wrong issuer
- `token_wrong_audience` - JWT with wrong audience
- `token_missing_scope` - User token with insufficient scope
- `token_missing_role` - App token with insufficient role

### HTTP Clients

- `client` - FastAPI TestClient (sync)
- `async_client` - AsyncClient (async)
- `mock_httpx_client` - Mock httpx client for JWKS fetching

### Auth Headers

- `auth_headers` - Authorization headers with valid user token
- `app_auth_headers` - Authorization headers with valid app token

### DCR Fixtures

- `vscode_dcr_request` - VS Code DCR request body
- `claude_code_dcr_request` - Claude Code DCR request body
- `vscode_user_agent` - VS Code User-Agent header
- `claude_code_user_agent` - Claude Code User-Agent header

## Test Examples

### Testing JWT Validation

```python
@pytest.mark.jwt
@pytest.mark.asyncio
async def test_custom_jwt_validation(jwt_validator, create_jwt_token):
    """Test JWT validation with custom claims."""
    claims = {
        "aud": "custom-audience",
        "iss": "custom-issuer",
        # ... other claims
    }
    token = create_jwt_token(claims)

    # Test validation
    with pytest.raises(TokenInvalidError):
        await jwt_validator.validate_token(token)
```

### Testing API Endpoints

```python
@pytest.mark.api
def test_custom_endpoint(client, auth_headers):
    """Test custom API endpoint."""
    response = client.get("/api/custom", headers=auth_headers)
    assert response.status_code == 200
```

### Testing with Mocks

```python
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_with_mock_jwks(jwt_validator):
    """Test with mocked JWKS."""
    with patch('app.auth.jwks_cache.JWKSCache.get_jwks') as mock_get:
        mock_get.return_value = {"keys": [...]}
        # Test code here
```

## Writing New Tests

### Test Naming Convention

- Test files: `test_<module>.py`
- Test classes: `Test<Component>`
- Test methods: `test_<description>`

### Good Test Structure

```python
@pytest.mark.<category>
def test_descriptive_name():
    """Clear docstring explaining what is tested."""
    # Arrange - Set up test data
    test_data = {...}

    # Act - Execute the code being tested
    result = function_under_test(test_data)

    # Assert - Verify the outcome
    assert result == expected_value
```

### Use Appropriate Markers

```python
@pytest.mark.unit  # Fast, isolated test
@pytest.mark.integration  # Requires external services
@pytest.mark.security  # Security-related
@pytest.mark.asyncio  # Async test
async def test_something():
    ...
```

## Continuous Integration

Tests are automatically run on:

- Every push to `main` or `develop`
- Every pull request

See `.github/workflows/ci.yml` for CI configuration.

### CI Test Matrix

- **Python versions**: 3.11, 3.12
- **Tests**: All tests with coverage
- **Linting**: flake8, mypy, black, isort
- **Security**: safety, bandit
- **Docker**: Build verification

## Test Performance

### Current Coverage

Run `make test-cov` to see current coverage metrics.

Target: **>80% coverage**

### Slow Tests

Tests marked with `@pytest.mark.slow` are excluded from quick runs:

```bash
# Run all except slow tests
pytest -m "not slow"

# Run only slow tests
pytest -m slow
```

## Debugging Tests

### Debug Mode

```bash
# Run with debugging output
pytest -vv -s --log-cli-level=DEBUG

# Or use make target
make test-debug
```

### Breakpoints

Use pytest's built-in breakpoint support:

```python
def test_something():
    value = calculate()
    import pdb; pdb.set_trace()  # Debugger will stop here
    assert value == expected
```

Or use `pytest --pdb` to drop into debugger on failures:

```bash
pytest --pdb
```

## Tips for Claude Code Users

### Quick Feedback Loop

```bash
# Start watch mode in one terminal
make watch

# Edit code/tests in another
# Tests auto-run on save!
```

### Fast Iteration

```bash
# Quick run (minimal output, fast)
make quick

# Run only failed tests
make test-failed
```

### Before Committing

```bash
# Run full CI checks locally
make ci

# Or individually
make ci-lint
make ci-format-check
make ci-test
```

## Common Issues

### Import Errors

If you see import errors,
ensure you're running pytest from the `mcp-server` directory:

```bash
cd mcp-server
pytest
```

### Mock Auth

Some tests may require ENABLE_MOCK_AUTH=false (set in conftest.py).
This prevents actual JWT validation during tests.

### Redis Tests

Integration tests that require Redis will be skipped if Redis is not running:

```bash
# Start Redis for integration tests
make redis-start

# Run integration tests
make test-integration

# Stop Redis
make redis-stop
```

### Coverage Not Updating

Clear pytest cache:

```bash
make clean
pytest
```

## Test Development Workflow

1. **Write failing test** - Define expected behavior
2. **Run test** - `pytest tests/test_module.py::test_name`
3. **Implement feature** - Write minimal code to pass
4. **Run test again** - Verify it passes
5. **Refactor** - Improve code quality
6. **Run all tests** - Ensure nothing broke

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio)
- [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
