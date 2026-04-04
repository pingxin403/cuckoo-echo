import { test, expect } from '@playwright/test';

/**
 * Visual regression tests — screenshot snapshots for each major page.
 * First run creates baseline screenshots; subsequent runs compare against them.
 * Seed credentials: admin@test.com / test123456
 */

async function loginAsAdmin(page: import('@playwright/test').Page) {
  await page.goto('/login');
  await page.fill('input[aria-label="邮箱"]', 'admin@test.com');
  await page.fill('input[aria-label="密码"]', 'test123456');
  await page.click('button[aria-label="登录"]');
  await expect(page).toHaveURL(/\/admin\/metrics/, { timeout: 10_000 });
}

test.describe('Visual regression (integration)', () => {
  test('login page screenshot', async ({ page }) => {
    await page.goto('/login');
    await expect(page.locator('h1')).toBeVisible();
    await expect(page).toHaveScreenshot('login-page.png', {
      maxDiffPixelRatio: 0.05,
    });
  });

  test('metrics dashboard screenshot', async ({ page }) => {
    await loginAsAdmin(page);
    await expect(page.locator('h1:has-text("数据看板")')).toBeVisible();
    // Wait for charts to render
    await page.waitForTimeout(1000);
    await expect(page).toHaveScreenshot('metrics-dashboard.png', {
      maxDiffPixelRatio: 0.1, // Charts may have minor rendering differences
    });
  });

  test('knowledge page screenshot', async ({ page }) => {
    await loginAsAdmin(page);
    await page.click('a[href="/admin/knowledge"]');
    await expect(page.locator('[aria-label="文档上传区域"]')).toBeVisible();
    await expect(page).toHaveScreenshot('knowledge-page.png', {
      maxDiffPixelRatio: 0.05,
    });
  });

  test('config page screenshot', async ({ page }) => {
    await loginAsAdmin(page);
    await page.click('a[href="/admin/config"]');
    await expect(page.locator('h1:has-text("配置中心")')).toBeVisible();
    await expect(page).toHaveScreenshot('config-page.png', {
      maxDiffPixelRatio: 0.05,
    });
  });

  test('sandbox page screenshot', async ({ page }) => {
    await loginAsAdmin(page);
    await page.click('a[href="/admin/sandbox"]');
    await expect(page.locator('h1:has-text("沙盒测试")')).toBeVisible();
    await expect(page).toHaveScreenshot('sandbox-page.png', {
      maxDiffPixelRatio: 0.05,
    });
  });

  test('hitl page screenshot', async ({ page }) => {
    await loginAsAdmin(page);
    await page.click('a[href="/admin/hitl"]');
    await expect(page.locator('h2:has-text("介入会话")')).toBeVisible();
    await expect(page).toHaveScreenshot('hitl-page.png', {
      maxDiffPixelRatio: 0.05,
    });
  });

  test('chat page screenshot', async ({ page }) => {
    await page.goto('/chat?api_key=ck_test_integration_key');
    await expect(page.locator('textarea[aria-label="消息输入框"]')).toBeVisible({
      timeout: 10_000,
    });
    await expect(page).toHaveScreenshot('chat-page.png', {
      maxDiffPixelRatio: 0.05,
    });
  });
});
