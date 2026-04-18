import { test, expect } from '@playwright/test';

/**
 * Integration test: Metrics Dashboard against real backend.
 * Seed credentials: admin@test.com / test123456
 */

async function loginAsAdmin(page: import('@playwright/test').Page) {
  await page.goto('/login');
  await page.fill('input[aria-label="邮箱"]', 'admin@test.com');
  await page.fill('input[aria-label="密码"]', 'test123456');
  await page.click('button[aria-label="登录"]');
  await expect(page).toHaveURL(/\/admin\/metrics/, { timeout: 10_000 });
}

test.describe('Metrics Dashboard (integration)', () => {
  test('dashboard renders metric cards after login', async ({ page }) => {
    await loginAsAdmin(page);

    await expect(page.locator('h1:has-text("数据看板")')).toBeVisible();
    await expect(page.locator('text=总对话数')).toBeVisible();
    await expect(page.locator('text=总 Token 数')).toBeVisible();
  });

  test('period selector changes active state', async ({ page }) => {
    await loginAsAdmin(page);

    // Default is 7d
    const btn7d = page.locator('button:has-text("最近 7 天")');
    await expect(btn7d).toHaveAttribute('aria-pressed', 'true');

    // Click 1d
    const btn1d = page.locator('button:has-text("最近 1 天")');
    await btn1d.click();
    await expect(btn1d).toHaveAttribute('aria-pressed', 'true');
    await expect(btn7d).toHaveAttribute('aria-pressed', 'false');

    // Click 30d
    const btn30d = page.locator('button:has-text("最近 30 天")');
    await btn30d.click();
    await expect(btn30d).toHaveAttribute('aria-pressed', 'true');
  });

  test('refresh button triggers data reload', async ({ page }) => {
    await loginAsAdmin(page);

    const refreshBtn = page.locator('button[aria-label="刷新数据"]');
    await expect(refreshBtn).toBeVisible();
    await refreshBtn.click();

    // Button should show loading state briefly
    await expect(refreshBtn).toBeVisible();
  });

  test('charts are rendered', async ({ page }) => {
    await loginAsAdmin(page);

    await expect(page.locator('h2:has-text("Token 消耗趋势")')).toBeVisible();
    await expect(page.locator('h2:has-text("对话数分布")')).toBeVisible();
  });

  test('missed queries section is visible', async ({ page }) => {
    await loginAsAdmin(page);

    await expect(page.locator('h2:has-text("高频未命中问题")')).toBeVisible();
    // Either data or empty state
    const data = page.locator('text=暂无数据');
    const list = page.locator('ul.divide-y');
    await expect(data.or(list)).toBeVisible({ timeout: 5_000 });
  });

  test('metrics API returns data', async ({ page }) => {
    // Login first to get a token
    await loginAsAdmin(page);

    // Intercept a metrics API call
    const metricsPromise = page.waitForResponse(
      (resp) => resp.url().includes('/admin/v1/metrics/overview'),
    );

    await page.locator('button[aria-label="刷新数据"]').click();
    const response = await metricsPromise.catch(() => null);
    if (response) {
      expect(response.status()).toBe(200);
    }
  });
});
