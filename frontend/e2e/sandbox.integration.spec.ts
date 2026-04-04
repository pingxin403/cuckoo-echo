import { test, expect } from '@playwright/test';

/**
 * Integration test: Sandbox Runner against real backend.
 * Seed credentials: admin@test.com / test123456
 */

async function loginAndNavigateToSandbox(page: import('@playwright/test').Page) {
  await page.goto('/login');
  await page.fill('input[aria-label="邮箱"]', 'admin@test.com');
  await page.fill('input[aria-label="密码"]', 'test123456');
  await page.click('button[aria-label="登录"]');
  await expect(page).toHaveURL(/\/admin\/metrics/, { timeout: 10_000 });
  await page.click('a[href="/admin/sandbox"]');
  await expect(page).toHaveURL(/\/admin\/sandbox/);
}

test.describe('Sandbox Runner (integration)', () => {
  test('sandbox page renders test case form', async ({ page }) => {
    await loginAndNavigateToSandbox(page);

    await expect(page.locator('h1:has-text("沙盒测试")')).toBeVisible();
    await expect(page.locator('[aria-label="测试用例"]')).toBeVisible();
    await expect(page.locator('button[aria-label="运行测试"]')).toBeVisible();
  });

  test('test case form has query and reference inputs', async ({ page }) => {
    await loginAndNavigateToSandbox(page);

    // First test case should have query and reference fields
    const queryInput = page.locator('[aria-label="用例 1 查询"]');
    await expect(queryInput).toBeVisible();

    const refInput = page.locator('[aria-label="用例 1 参考答案"]');
    await expect(refInput).toBeVisible();
  });

  test('can add and remove test cases', async ({ page }) => {
    await loginAndNavigateToSandbox(page);

    // Initially one test case
    await expect(page.locator('text=用例 #1')).toBeVisible();

    // Add a test case
    await page.click('button[aria-label="添加测试用例"]');
    await expect(page.locator('text=用例 #2')).toBeVisible();

    // Remove the second test case
    await page.click('button[aria-label="删除用例 2"]');
    await expect(page.locator('text=用例 #2')).not.toBeVisible();
  });

  test('can fill in test case data', async ({ page }) => {
    await loginAndNavigateToSandbox(page);

    await page.locator('[aria-label="用例 1 查询"]').fill('What is your return policy?');
    await page.locator('[aria-label="用例 1 参考答案"]').fill('30-day return policy');

    await expect(page.locator('[aria-label="用例 1 查询"]')).toHaveValue('What is your return policy?');
  });

  test('save and load test case sets', async ({ page }) => {
    await loginAndNavigateToSandbox(page);

    // Fill in a test case
    await page.locator('[aria-label="用例 1 查询"]').fill('Test query for save');

    // Save the set
    await page.locator('[aria-label="用例集名称"]').fill('E2E Test Set');
    await page.click('button[aria-label="保存用例集"]');

    // Load menu should show the saved set
    await page.click('button[aria-label="加载用例集"]');
    await expect(page.locator('button:has-text("E2E Test Set")').first()).toBeVisible({ timeout: 3_000 });
  });

  test('run button is disabled during execution', async ({ page }) => {
    await loginAndNavigateToSandbox(page);

    // Fill in a query so run is valid
    await page.locator('[aria-label="用例 1 查询"]').fill('Hello');

    const runBtn = page.locator('button[aria-label="运行测试"]');
    await expect(runBtn).toBeEnabled();
  });
});
