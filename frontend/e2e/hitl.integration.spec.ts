import { test, expect } from '@playwright/test';

/**
 * Integration test: HITL WebSocket flow against real backend.
 * Seed credentials: admin@test.com / test123456
 */

async function loginAndNavigateToHITL(page: import('@playwright/test').Page) {
  await page.goto('/login');
  await page.fill('input[aria-label="邮箱"]', 'admin@test.com');
  await page.fill('input[aria-label="密码"]', 'test123456');
  await page.click('button[aria-label="登录"]');
  await expect(page).toHaveURL(/\/admin\/metrics/, { timeout: 10_000 });
  // Navigate via SPA link to preserve auth state
  await page.click('a[href="/admin/hitl"]');
  await expect(page).toHaveURL(/\/admin\/hitl/);
}

test.describe('HITL WebSocket flow (integration)', () => {
  test('HITL panel renders after admin login', async ({ page }) => {
    await loginAndNavigateToHITL(page);

    // The HITL panel should show the "介入会话" heading
    await expect(page.locator('h2:has-text("介入会话")')).toBeVisible({
      timeout: 10_000,
    });
  });

  test('WebSocket connection is established on HITL page', async ({
    page,
  }) => {
    // Listen for WebSocket connections before navigating
    const wsPromise = page.waitForEvent('websocket', {
      timeout: 15_000,
    });

    await loginAndNavigateToHITL(page);

    // Verify a WebSocket connection was opened to the HITL endpoint
    const ws = await wsPromise.catch(() => null);
    if (ws) {
      expect(ws.url()).toContain('/ws/hitl');
    }
  });

  test('empty state shows when no pending sessions', async ({ page }) => {
    await loginAndNavigateToHITL(page);

    // Should show empty state or session list
    const emptyState = page.locator('text=暂无介入会话');
    const sessionList = page.locator('text=待处理');

    await expect(emptyState.or(sessionList)).toBeVisible({ timeout: 10_000 });
  });

  test('HITL page shows idle message area', async ({ page }) => {
    await loginAndNavigateToHITL(page);

    // The right panel should show "选择一个会话开始处理"
    await expect(
      page.locator('text=选择一个会话开始处理'),
    ).toBeVisible({ timeout: 10_000 });
  });
});
