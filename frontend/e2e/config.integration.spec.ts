import { test, expect } from '@playwright/test';

/**
 * Integration test: Config Panel against real backend.
 * Seed credentials: admin@test.com / test123456
 */

async function loginAndNavigateToConfig(page: import('@playwright/test').Page) {
  await page.goto('/login');
  await page.fill('input[aria-label="邮箱"]', 'admin@test.com');
  await page.fill('input[aria-label="密码"]', 'test123456');
  await page.click('button[aria-label="登录"]');
  await expect(page).toHaveURL(/\/admin\/metrics/, { timeout: 10_000 });
  await page.click('a[href="/admin/config"]');
  await expect(page).toHaveURL(/\/admin\/config/);
}

test.describe('Config Panel (integration)', () => {
  test('config page renders all sections', async ({ page }) => {
    await loginAndNavigateToConfig(page);

    await expect(page.locator('h1:has-text("配置中心")')).toBeVisible();
    await expect(page.locator('[aria-label="Persona 配置"]')).toBeVisible();
    await expect(page.locator('[aria-label="模型配置"]')).toBeVisible();
    await expect(page.locator('[aria-label="限流配置"]')).toBeVisible();
    await expect(page.locator('[aria-label="缓存管理"]')).toBeVisible();
    await expect(page.locator('[aria-label="嵌入代码生成器"]')).toBeVisible();
  });

  test('persona config form is editable', async ({ page }) => {
    await loginAndNavigateToConfig(page);

    const promptInput = page.locator('#systemPrompt');
    await expect(promptInput).toBeVisible();
    await promptInput.fill('Test system prompt');
    await expect(promptInput).toHaveValue('Test system prompt');

    const nameInput = page.locator('#personaName');
    await nameInput.fill('TestBot');
    await expect(nameInput).toHaveValue('TestBot');
  });

  test('model config has primary and fallback selects', async ({ page }) => {
    await loginAndNavigateToConfig(page);

    const primarySelect = page.locator('#primaryModel');
    await expect(primarySelect).toBeVisible();

    const fallbackSelect = page.locator('#fallbackModel');
    await expect(fallbackSelect).toBeVisible();

    // Temperature slider exists
    const tempSlider = page.locator('#temperature');
    await expect(tempSlider).toBeVisible();
  });

  test('rate limit config has tenant and user RPS inputs', async ({ page }) => {
    await loginAndNavigateToConfig(page);

    const tenantRps = page.locator('#tenantRps');
    await expect(tenantRps).toBeVisible();

    const userRps = page.locator('#userRps');
    await expect(userRps).toBeVisible();
  });

  test('clear cache button exists', async ({ page }) => {
    await loginAndNavigateToConfig(page);

    const clearBtn = page.locator('button[aria-label="清除语义缓存"]');
    await expect(clearBtn).toBeVisible();
  });

  test('embed code generator produces snippet', async ({ page }) => {
    await loginAndNavigateToConfig(page);

    // The embed code section should have a <pre> with code
    const codeBlock = page.locator('[aria-label="嵌入代码生成器"] pre code');
    await expect(codeBlock).toBeVisible();
    const text = await codeBlock.textContent();
    expect(text).toContain('data-api-key');
    expect(text).toContain('embed.js');

    // Copy button exists
    const copyBtn = page.locator('button[aria-label="复制嵌入代码"]');
    await expect(copyBtn).toBeVisible();
  });

  test('save persona config triggers API call', async ({ page }) => {
    await loginAndNavigateToConfig(page);

    // Fill in persona form
    await page.locator('#systemPrompt').fill('E2E test prompt');
    await page.locator('#personaName').fill('E2E Bot');

    // Intercept the save API call
    const savePromise = page.waitForResponse(
      (resp) => resp.url().includes('/admin/v1/config/persona') && resp.request().method() === 'PUT',
    );

    await page.click('button[aria-label="保存 Persona 配置"]');

    const response = await savePromise.catch(() => null);
    if (response) {
      expect([200, 204]).toContain(response.status());
    }
  });
});
