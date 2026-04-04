import { test, expect } from '@playwright/test';

/**
 * Helper: log in as admin before each knowledge test.
 */
async function loginAsAdmin(page: import('@playwright/test').Page) {
  await page.goto('/login');
  await page.fill('input[aria-label="邮箱"]', 'admin@example.com');
  await page.fill('input[aria-label="密码"]', 'password');
  await page.click('button[aria-label="登录"]');
  await expect(page).toHaveURL(/\/admin\/metrics/);
}

test.describe('Knowledge management', () => {
  test('knowledge page renders upload zone', async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto('/admin/knowledge');

    // The upload zone should be visible
    await expect(page.locator('[aria-label="文档上传区域"]')).toBeVisible();
    await expect(page.locator('text=选择文件')).toBeVisible();
    await expect(page.locator('text=支持 PDF、DOCX、HTML、TXT，最大 50MB')).toBeVisible();
  });

  test('document list renders after API response', async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto('/admin/knowledge');

    // Wait for the document list to load (either documents or empty state)
    const hasDocuments = page.locator('table').first();
    const emptyState = page.locator('text=暂无文档');

    await expect(hasDocuments.or(emptyState)).toBeVisible({ timeout: 10_000 });
  });
});
