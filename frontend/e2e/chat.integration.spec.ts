import { test, expect } from '@playwright/test';

/**
 * Integration test: Chat with seed API key against real backend.
 * Seed API key: ck_test_integration_key
 */
test.describe('Chat flow (integration)', () => {
  const API_KEY = 'ck_test_integration_key';

  test('send message and receive SSE streaming response', async ({ page }) => {
    await page.goto(`/chat?api_key=${API_KEY}`);

    // Type and send a message
    const input = page.locator('textarea[aria-label="消息输入框"]');
    await input.fill('Hello, can you help me?');
    await page.click('button[aria-label="发送消息"]');

    // Optimistic user message should appear
    await expect(page.locator('text=Hello, can you help me?')).toBeVisible({
      timeout: 5_000,
    });

    // Wait for assistant response bubble (SSE streaming or completed)
    // Ollama local models may take longer to respond
    await expect(
      page.locator('[data-testid="message-bubble"]').nth(1),
    ).toBeVisible({ timeout: 60_000 });
  });

  test('SSE stream completes and message is finalized', async ({ page }) => {
    await page.goto(`/chat?api_key=${API_KEY}`);

    const input = page.locator('textarea[aria-label="消息输入框"]');
    await input.fill('What is 2+2?');
    await page.click('button[aria-label="发送消息"]');

    // Wait for streaming to complete — the send button should become enabled again
    // Ollama local models may take longer
    await expect(page.locator('button[aria-label="发送消息"]')).toBeEnabled({
      timeout: 60_000,
    });

    // At least two message bubbles should exist (user + assistant)
    const bubbles = page.locator('[data-testid="message-bubble"]');
    await expect(bubbles).toHaveCount(2, { timeout: 5_000 });
  });

  test('chat page loads with valid API key', async ({ page }) => {
    await page.goto(`/chat?api_key=${API_KEY}`);

    // Chat input should be visible and ready
    await expect(page.locator('textarea[aria-label="消息输入框"]')).toBeVisible({
      timeout: 10_000,
    });
  });
});
