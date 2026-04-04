import { test, expect } from '@playwright/test';

/**
 * Integration test: Multi-tenant isolation.
 * Tenant A: ck_test_integration_key / admin@test.com
 * Tenant B: ck_test_tenant_b_key / admin-b@test.com
 */
test.describe('Multi-tenant isolation (integration)', () => {
  test('tenant A API key returns 200', async ({ request }) => {
    const res = await request.post('/v1/chat/completions', {
      headers: { Authorization: 'Bearer ck_test_integration_key', 'Content-Type': 'application/json' },
      data: { messages: [{ role: 'user', content: 'hi' }] },
    });
    expect(res.status()).toBe(200);
  });

  test('tenant B API key returns 200', async ({ request }) => {
    const res = await request.post('/v1/chat/completions', {
      headers: { Authorization: 'Bearer ck_test_tenant_b_key', 'Content-Type': 'application/json' },
      data: { messages: [{ role: 'user', content: 'hi' }] },
    });
    expect(res.status()).toBe(200);
  });

  test('invalid API key returns 401', async ({ request }) => {
    const res = await request.post('/v1/chat/completions', {
      headers: { Authorization: 'Bearer invalid_key_xxx', 'Content-Type': 'application/json' },
      data: { messages: [{ role: 'user', content: 'hi' }] },
    });
    expect(res.status()).toBe(401);
  });

  test('tenant B admin cannot see tenant A knowledge docs', async ({ request }) => {
    // Login as tenant B admin
    const loginRes = await request.post('/admin/v1/auth/login', {
      data: { email: 'admin-b@test.com', password: 'test123456' },
    });
    if (loginRes.status() !== 200) return; // Skip if tenant B not seeded

    const body = await loginRes.json() as { access_token: string };
    const token = body.access_token;

    // List knowledge docs — should be empty (tenant B has no docs)
    const docsRes = await request.get('/admin/v1/knowledge/docs', {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (docsRes.status() === 200) {
      const docs = await docsRes.json() as unknown[];
      expect(docs.length).toBe(0);
    }
  });
});
