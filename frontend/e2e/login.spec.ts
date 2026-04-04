import { test, expect } from '@playwright/test';

test.describe('Login flow', () => {
  test('login with valid credentials redirects to /admin/metrics', async ({ page }) => {
    await page.goto('/login');

    await page.fill('input[aria-label="邮箱"]', 'admin@example.com');
    await page.fill('input[aria-label="密码"]', 'password');
    await page.click('button[aria-label="登录"]');

    await expect(page).toHaveURL(/\/admin\/metrics/);
  });

  test('unauthenticated access to /admin redirects to /login', async ({ page }) => {
    await page.goto('/admin/metrics');

    await expect(page).toHaveURL(/\/login/);
  });

  test('invalid credentials shows error message', async ({ page }) => {
    await page.goto('/login');

    await page.fill('input[aria-label="邮箱"]', 'wrong@example.com');
    await page.fill('input[aria-label="密码"]', 'wrongpassword');
    await page.click('button[aria-label="登录"]');

    // Should stay on login page and show error toast
    await expect(page).toHaveURL(/\/login/);
    await expect(page.locator('text=邮箱或密码错误')).toBeVisible();
  });
});
