import { test, expect } from '@playwright/test';

/**
 * Integration test: Chat with seed API key against real backend.
 * Seed API key: ck_test_integration_key
 */
test.describe('Chat flow (integration)', () => {
  const API_KEY = 'ck_test_integration_key';

  test('send message and SSE request is made', async ({ page }) => {
    await page.goto(`/chat?api_key=${API_KEY}`);

    // Type and send a message
    const input = page.locator('textarea[aria-label="消息输入框"]');
    await input.fill('Hello, can you help me?');
    await page.click('button[aria-label="发送消息"]');

    // Optimistic user message should appear
    await expect(page.locator('text=Hello, can you help me?')).toBeVisible({
      timeout: 5_000,
    });

    // Should show "AI 正在思考" or an assistant response
    const thinking = page.locator('text=AI 正在思考');
    const assistantBubble = page.locator('[data-testid="message-bubble"]').nth(1);
    await expect(thinking.or(assistantBubble)).toBeVisible({ timeout: 15_000 });
  });

  test('chat API returns SSE response', async ({ request }) => {
    // Direct API test — verify SSE endpoint is reachable and authenticated
    const response = await request.post('/v1/chat/completions', {
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'Content-Type': 'application/json',
      },
      data: {
        messages: [{ role: 'user', content: 'Hi' }],
      },
    });

    // Should get 200 (SSE stream) not 401 or 404
    expect(response.status()).toBe(200);
  });

  test('chat page loads with valid API key', async ({ page }) => {
    await page.goto(`/chat?api_key=${API_KEY}`);

    // Chat input should be visible and ready
    await expect(page.locator('textarea[aria-label="消息输入框"]')).toBeVisible({
      timeout: 10_000,
    });
  });
});
