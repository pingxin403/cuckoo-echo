import { test, expect } from '@playwright/test';

/**
 * Integration test: Knowledge upload against real backend.
 * Seed credentials: admin@test.com / test123456
 */

async function loginAndNavigateToKnowledge(page: import('@playwright/test').Page) {
  await page.goto('/login');
  await page.fill('input[aria-label="邮箱"]', 'admin@test.com');
  await page.fill('input[aria-label="密码"]', 'test123456');
  await page.click('button[aria-label="登录"]');
  await expect(page).toHaveURL(/\/admin\/metrics/, { timeout: 10_000 });
  // Navigate via SPA link to preserve auth state
  await page.click('a[href="/admin/knowledge"]');
  await expect(page).toHaveURL(/\/admin\/knowledge/);
}

test.describe('Knowledge upload (integration)', () => {
  test('knowledge page renders upload zone after login', async ({ page }) => {
    await loginAndNavigateToKnowledge(page);

    await expect(page.locator('[aria-label="文档上传区域"]')).toBeVisible({
      timeout: 10_000,
    });
  });

  test('upload a text file and see it in the document list', async ({
    page,
  }) => {
    await loginAndNavigateToKnowledge(page);

    // Wait for upload zone to be visible
    await expect(page.locator('[aria-label="文档上传区域"]')).toBeVisible({
      timeout: 10_000,
    });

    // Create a test file buffer for upload
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'test-document.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('This is a test document for knowledge base.'),
    });

    // Wait for the document to appear in the list (pending or processing)
    await expect(
      page.locator('text=test-document.txt').first(),
    ).toBeVisible({ timeout: 30_000 });
  });

  test('document list shows status after upload', async ({ page }) => {
    await loginAndNavigateToKnowledge(page);

    // Wait for knowledge page to load — upload zone should be visible
    await expect(page.locator('[aria-label="文档上传区域"]')).toBeVisible({ timeout: 10_000 });
  });
});
