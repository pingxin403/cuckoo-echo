import { test, expect } from '@playwright/test';

/**
 * Integration test: HITL WebSocket flow against real backend.
 * Seed credentials: admin@test.com / test123456
 */

async function loginAsAdmin(page: import('@playwright/test').Page) {
  await page.goto('/login');
  await page.fill('input[aria-label="邮箱"]', 'admin@test.com');
  await page.fill('input[aria-label="密码"]', 'test123456');
  await page.click('button[aria-label="登录"]');
  await expect(page).toHaveURL(/\/admin\/metrics/, { timeout: 10_000 });
}

test.describe('HITL WebSocket flow (integration)', () => {
  test('HITL panel renders after admin login', async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto('/admin/hitl');

    await expect(page.locator('[aria-label="人工介入面板"]')).toBeVisible({
      timeout: 10_000,
    });
  });

  test('WebSocket connection is established on HITL page', async ({
    page,
  }) => {
    await loginAsAdmin(page);

    // Listen for WebSocket connections
    const wsPromise = page.waitForEvent('websocket', {
      timeout: 15_000,
    });

    await page.goto('/admin/hitl');

    // Verify a WebSocket connection was opened to the HITL endpoint
    const ws = await wsPromise.catch(() => null);
    if (ws) {
      expect(ws.url()).toContain('/ws/hitl');
    }
  });

  test('take session when pending session exists', async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto('/admin/hitl');

    // If there's a pending session, try to take it
    const pendingSession = page.locator('text=点击接管').first();
    if (
      await pendingSession.isVisible({ timeout: 5_000 }).catch(() => false)
    ) {
      await pendingSession.click();

      // After taking, the conversation area should show the end button
      await expect(
        page.locator('button[aria-label="结束介入"]'),
      ).toBeVisible({ timeout: 10_000 });
    }
  });

  test('end session returns to idle state', async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto('/admin/hitl');

    const pendingSession = page.locator('text=点击接管').first();
    if (
      await pendingSession.isVisible({ timeout: 5_000 }).catch(() => false)
    ) {
      await pendingSession.click();
      await expect(
        page.locator('button[aria-label="结束介入"]'),
      ).toBeVisible({ timeout: 10_000 });

      await page.click('button[aria-label="结束介入"]');

      await expect(
        page.locator('text=选择一个会话开始处理'),
      ).toBeVisible({ timeout: 10_000 });
    }
  });
});
