import { test, expect } from '@playwright/test';

/**
 * Helper: log in as admin before each HITL test.
 */
async function loginAsAdmin(page: import('@playwright/test').Page) {
  await page.goto('/login');
  await page.fill('input[aria-label="邮箱"]', 'admin@example.com');
  await page.fill('input[aria-label="密码"]', 'password');
  await page.click('button[aria-label="登录"]');
  await expect(page).toHaveURL(/\/admin\/metrics/);
}

test.describe('HITL panel', () => {
  test('HITL panel shows session list', async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto('/admin/hitl');

    // The panel should render with the session list area
    await expect(page.locator('[aria-label="人工介入面板"]')).toBeVisible();
    await expect(page.locator('text=介入会话')).toBeVisible();
  });

  test('take session loads conversation', async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto('/admin/hitl');

    // If there's a pending session, clicking it should trigger "take"
    const pendingSession = page.locator('text=点击接管').first();
    if (await pendingSession.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await pendingSession.click();
      // After taking, the conversation area should show the session header
      await expect(page.locator('button[aria-label="结束介入"]')).toBeVisible({
        timeout: 5_000,
      });
    }
  });

  test('end session returns to idle state', async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto('/admin/hitl');

    // Take a session first if available
    const pendingSession = page.locator('text=点击接管').first();
    if (await pendingSession.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await pendingSession.click();
      await expect(page.locator('button[aria-label="结束介入"]')).toBeVisible({
        timeout: 5_000,
      });

      // End the session
      await page.click('button[aria-label="结束介入"]');

      // Should return to idle — the placeholder text should be visible
      await expect(page.locator('text=选择一个会话开始处理')).toBeVisible({
        timeout: 5_000,
      });
    }
  });
});
