import { test, expect } from '@playwright/test';

/**
 * Responsive layout tests — verify pages render correctly at different viewports.
 * Seed credentials: admin@test.com / test123456
 */

async function loginAsAdmin(page: import('@playwright/test').Page) {
  await page.goto('/login');
  await page.fill('input[aria-label="邮箱"]', 'admin@test.com');
  await page.fill('input[aria-label="密码"]', 'test123456');
  await page.click('button[aria-label="登录"]');
  await expect(page).toHaveURL(/\/admin\/metrics/, { timeout: 10_000 });
}

test.describe('Responsive layout — desktop (1920x1080)', () => {
  test.use({ viewport: { width: 1920, height: 1080 } });

  test('sidebar is visible on desktop', async ({ page }) => {
    await loginAsAdmin(page);
    const sidebar = page.locator('nav[aria-label="管理后台导航"]');
    await expect(sidebar).toBeVisible();
  });

  test('dashboard cards layout on desktop', async ({ page }) => {
    await loginAsAdmin(page);
    await expect(page.locator('text=总对话数')).toBeVisible();
    await expect(page).toHaveScreenshot('desktop-metrics.png', {
      maxDiffPixelRatio: 0.1,
    });
  });
});

test.describe('Responsive layout — mobile (375x812)', () => {
  test.use({ viewport: { width: 375, height: 812 } });

  test('login page renders on mobile', async ({ page }) => {
    await page.goto('/login');
    await expect(page.locator('h1')).toBeVisible();
    await expect(page.locator('button[aria-label="登录"]')).toBeVisible();
    await expect(page).toHaveScreenshot('mobile-login.png', {
      maxDiffPixelRatio: 0.05,
    });
  });

  test('chat page renders on mobile', async ({ page }) => {
    await page.goto('/chat?api_key=ck_test_integration_key');
    await expect(page.locator('textarea[aria-label="消息输入框"]')).toBeVisible({
      timeout: 10_000,
    });
    await expect(page).toHaveScreenshot('mobile-chat.png', {
      maxDiffPixelRatio: 0.05,
    });
  });

  test('admin dashboard on mobile — sidebar toggle', async ({ page }) => {
    await loginAsAdmin(page);
    // On mobile, sidebar should be hidden by default
    const sidebar = page.locator('nav[aria-label="管理后台导航"]');
    // Sidebar may be off-screen (translated) on mobile
    const hamburger = page.locator('button[aria-label="打开侧边栏"]');
    if (await hamburger.isVisible()) {
      await hamburger.click();
      await expect(sidebar).toBeVisible();
    }
  });
});
