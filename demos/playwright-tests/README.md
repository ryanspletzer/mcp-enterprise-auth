# Playwright E2E Tests

End-to-end browser automation tests for the mock Entra ID and MCP server integration.

## Setup

```bash
# Install dependencies
npm install

# Install Playwright browsers
npx playwright install chromium
```

## Running Tests

```bash
# Run all tests
npm test

# Run tests in headed mode (see browser)
npm run test:headed

# Run tests in debug mode
npm run test:debug

# Run tests with UI
npm run test:ui

# Show test report
npm run show-report
```

## Test Coverage

### Service Principal Flow

- ✅ Client credentials grant
- ✅ App-only token validation
- ✅ MCP server authentication
- ✅ MCP protocol initialization
- ✅ Error handling (invalid credentials)

### Future Tests

- Authorization code + PKCE flow (requires browser interaction)
- Refresh token flow
- PKCE validation
- Token expiration handling

## Configuration

The Playwright config (`playwright.config.ts`) automatically:

- Starts Docker Compose services before tests
- Waits for services to be healthy
- Runs tests against localhost:8001 (mock IdP) and localhost:8000 (MCP server)
- Generates HTML reports

## Writing New Tests

```typescript
import { test, expect } from '@playwright/test';

test('my test', async ({ request, page }) => {
  // Use 'request' for API calls
  // Use 'page' for browser automation
});
```

## CI/CD Integration

The tests are configured to run in CI environments with:

- Retries on failure
- Serial execution (1 worker)
- Auto-starting services with Docker Compose

Add to your CI pipeline:
```yaml
- name: Run E2E tests
  run: |
    cd demos/playwright-tests
    npm install
    npm test
```
