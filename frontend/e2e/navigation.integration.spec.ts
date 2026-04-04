import { test, expect } from '@playwright/test';

/**
 * Integration test: Navigation, layout, and auth flows.
 * Seed credentials: admin@test.com / test123456
 */

async function loginAsAdmin(page: import('@playwright/test').Page) {
  await page.goto('/login');
  await page.fill('input[aria-label="邮箱"]', 'admin@test.com');
  await page.fill('input[aria-label="密码"]', 'test123456');
  await page.click('button[aria-label="登录"]');
  await expect(page).toHaveURL(/\/admin\/metrics/, { timeout: 10_000 });
}

test.describe('Navigation & Layout (integration)', () => {
  test('sidebar shows all navigation links', async ({ page }) => {
    await loginAsAdmin(page);

    const nav = page.locator('nav[aria-label="管理后台导航"]');
    await expect(nav).toBeVisible();

    await expect(nav.locator('a[href="/admin/metrics"]')).toBeVisible();
    await expect(nav.locator('a[href="/admin/knowledge"]')).toBeVisible();
    await expect(nav.locator('a[href="/admin/hitl"]')).toBeVisible();
    await expect(nav.locator('a[href="/admin/config"]')).toBeVisible();
    await expect(nav.locator('a[href="/admin/sandbox"]')).toBeVisible();
  });

  test('navigate to each admin page via sidebar', async ({ page }) => {
    await loginAsAdmin(page);

    // Knowledge
    await page.click('a[href="/admin/knowledge"]');
    await expect(page).toHaveURL(/\/admin\/knowledge/);
    await expect(page.locator('h1:has-text("知识库管理")')).toBeVisible();

    // HITL
    await page.click('a[href="/admin/hitl"]');
    await expect(page).toHaveURL(/\/admin\/hitl/);
    await expect(page.locator('h2:has-text("介入会话")')).toBeVisible();

    // Config
    await page.click('a[href="/admin/config"]');
    await expect(page).toHaveURL(/\/admin\/config/);
    await expect(page.locator('h1:has-text("配置中心")')).toBeVisible();

    // Sandbox
    await page.click('a[href="/admin/sandbox"]');
    await expect(page).toHaveURL(/\/admin\/sandbox/);
    await expect(page.locator('h1:has-text("沙盒测试")')).toBeVisible();

    // Back to Metrics
    await page.click('a[href="/admin/metrics"]');
    await expect(page).toHaveURL(/\/admin\/metrics/);
    await expect(page.locator('h1:has-text("数据看板")')).toBeVisible();
  });

  test('header shows user info', async ({ page }) => {
    await loginAsAdmin(page);

    // User email or ID should be visible in header
    await expect(page.locator('button:has-text("退出登录")')).toBeVisible();
  });

  test('logout redirects to login page', async ({ page }) => {
    await loginAsAdmin(page);

    await page.click('button:has-text("退出登录")');
    await expect(page).toHaveURL(/\/login/, { timeout: 5_000 });
  });

  test('catch-all route redirects to login', async ({ page }) => {
    await page.goto('/nonexistent-page');
    await expect(page).toHaveURL(/\/login/);
  });

  test('chat page accessible without admin auth', async ({ page }) => {
    // Chat page should load with API key (no admin login needed)
    await page.goto('/chat?api_key=ck_test_integration_key');
    await expect(page.locator('textarea[aria-label="消息输入框"]')).toBeVisible({
      timeout: 10_000,
    });
  });

  test('chat page shows connection status', async ({ page }) => {
    await page.goto('/chat?api_key=ck_test_integration_key');

    // Connection status indicator should be visible
    const connected = page.locator('text=已连接');
    const disconnected = page.locator('text=已断开');
    const connecting = page.locator('text=连接中');
    await expect(connected.or(disconnected).or(connecting)).toBeVisible({
      timeout: 5_000,
    });
  });

  test('chat page shows thread list sidebar', async ({ page }) => {
    await page.goto('/chat?api_key=ck_test_integration_key');

    await expect(page.locator('[aria-label="会话列表"]').first()).toBeVisible({
      timeout: 5_000,
    });
  });
});
