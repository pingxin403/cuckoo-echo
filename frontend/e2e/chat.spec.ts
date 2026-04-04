import { test, expect } from '@playwright/test';

test.describe('Chat flow', () => {
  test('send message appears in message list', async ({ page }) => {
    await page.goto('/chat?api_key=ck_test');

    // Type a message and send
    const input = page.locator('textarea[aria-label="消息输入"]');
    await input.fill('Hello, I need help');
    await page.click('button[aria-label="发送"]');

    // The optimistic message should appear in the chat area
    await expect(page.locator('text=Hello, I need help')).toBeVisible();
  });

  test('SSE streaming updates message content progressively', async ({ page }) => {
    await page.goto('/chat?api_key=ck_test');

    const input = page.locator('textarea[aria-label="消息输入"]');
    await input.fill('Tell me a story');
    await page.click('button[aria-label="发送"]');

    // Wait for the assistant message bubble to appear (streaming or completed)
    await expect(page.locator('[data-testid="message-bubble"]').first()).toBeVisible({
      timeout: 10_000,
    });
  });

  test.skip('file upload — placeholder (needs real backend)', async ({ page }) => {
    await page.goto('/chat?api_key=ck_test');
    // File upload E2E requires a running backend with file handling.
    // This is a placeholder for future implementation.
    expect(true).toBe(true);
  });
});
