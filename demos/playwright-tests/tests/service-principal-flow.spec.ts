import { test, expect } from '@playwright/test';

test.describe('Service Principal Client Credentials Flow', () => {
  test('should obtain app-only token and call MCP server', async ({ request }) => {
    // Step 1: Get app-only token via client_credentials grant
    const tokenResponse = await request.post('http://localhost:8001/oauth2/v2.0/token', {
      form: {
        grant_type: 'client_credentials',
        client_id: '77777777-7777-7777-7777-777777777777',
        client_secret: 'test-sp-secret-456',
        scope: 'api://mcp-server/.default',
      },
    });

    expect(tokenResponse.ok()).toBeTruthy();
    const tokens = await tokenResponse.json();

    expect(tokens).toHaveProperty('access_token');
    expect(tokens).toHaveProperty('token_type', 'Bearer');
    expect(tokens).toHaveProperty('expires_in');
    expect(tokens).not.toHaveProperty('refresh_token'); // No refresh for app-only

    // Step 2: Decode token to verify claims
    const accessToken = tokens.access_token;
    const payload = JSON.parse(
      Buffer.from(accessToken.split('.')[1], 'base64').toString()
    );

    expect(payload).toHaveProperty('idtyp', 'app'); // Critical app-only indicator
    expect(payload).toHaveProperty('roles');
    expect(Array.isArray(payload.roles)).toBeTruthy();
    expect(payload.roles).toContain('MCP.ReadWrite.All');

    // Step 3: Call MCP server /api/me endpoint
    const meResponse = await request.get('http://localhost:8000/api/me', {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });

    expect(meResponse.ok()).toBeTruthy();
    const identity = await meResponse.json();

    expect(identity).toHaveProperty('token_type', 'app_only');
    expect(identity.identity).toHaveProperty('app_id');
    expect(identity.permissions).toHaveProperty('roles');

    // Step 4: Call MCP initialize endpoint
    const initResponse = await request.post('http://localhost:8000/mcp/initialize', {
      headers: {
        Authorization: `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      data: {
        protocolVersion: '2024-11-05',
        capabilities: {},
        clientInfo: {
          name: 'Playwright Test Client',
          version: '1.0.0',
        },
      },
    });

    expect(initResponse.ok()).toBeTruthy();
    const initData = await initResponse.json();

    expect(initData).toHaveProperty('protocolVersion');
    expect(initData).toHaveProperty('capabilities');
    expect(initData.capabilities).toHaveProperty('tools');
    expect(initData.capabilities).toHaveProperty('resources');
    expect(initData.capabilities).toHaveProperty('prompts');
  });

  test('should reject invalid client credentials', async ({ request }) => {
    const tokenResponse = await request.post('http://localhost:8001/oauth2/v2.0/token', {
      form: {
        grant_type: 'client_credentials',
        client_id: '77777777-7777-7777-7777-777777777777',
        client_secret: 'wrong-secret',
        scope: 'api://mcp-server/.default',
      },
    });

    expect(tokenResponse.status()).toBe(400);
    const error = await tokenResponse.json();
    expect(error.detail).toHaveProperty('error', 'invalid_client');
  });
});
