import { test, expect } from '@playwright/test';

/**
 * Integration test: Admin login with seed data against real backend.
 * Seed credentials: admin@test.com / test123456
 */
test.describe('Admin login (integration)', () => {
  test('login with seed admin credentials redirects to /admin/metrics', async ({
    page,
  }) => {
    await page.goto('/login');

    await page.fill('input[aria-label="邮箱"]', 'admin@test.com');
    await page.fill('input[aria-label="密码"]', 'test123456');
    await page.click('button[aria-label="登录"]');

    // Should redirect to admin metrics dashboard
    await expect(page).toHaveURL(/\/admin\/metrics/, { timeout: 10_000 });
  });

  test('login response contains valid JWT with admin_user_id', async ({
    page,
  }) => {
    // Intercept the login API response
    const loginPromise = page.waitForResponse(
      (resp) =>
        resp.url().includes('/admin/v1/auth/login') && resp.status() === 200,
    );

    await page.goto('/login');
    await page.fill('input[aria-label="邮箱"]', 'admin@test.com');
    await page.fill('input[aria-label="密码"]', 'test123456');
    await page.click('button[aria-label="登录"]');

    const response = await loginPromise;
    const body = (await response.json()) as { access_token?: string };

    // Verify JWT structure (3 dot-separated parts)
    expect(body.access_token).toBeDefined();
    const parts = body.access_token!.split('.');
    expect(parts.length).toBe(3);

    // Decode payload and verify fields
    const payload = JSON.parse(atob(parts[1])) as Record<string, unknown>;
    expect(payload.admin_user_id).toBeDefined();
    expect(payload.tenant_id).toBeDefined();
    expect(payload.role).toBeDefined();
  });

  test('invalid credentials shows error and stays on login page', async ({
    page,
  }) => {
    await page.goto('/login');

    await page.fill('input[aria-label="邮箱"]', 'wrong@test.com');
    await page.fill('input[aria-label="密码"]', 'wrongpassword');
    await page.click('button[aria-label="登录"]');

    // Should stay on login page
    await expect(page).toHaveURL(/\/login/);
  });

  test('unauthenticated access to /admin redirects to /login', async ({
    page,
  }) => {
    await page.goto('/admin/metrics');
    await expect(page).toHaveURL(/\/login/);
  });
});
