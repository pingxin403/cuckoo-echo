# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: metrics.integration.spec.ts >> Metrics Dashboard (integration) >> missed queries section is visible
- Location: e2e/metrics.integration.spec.ts:62:3

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('text=暂无数据').or(locator('ul.divide-y'))
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for locator('text=暂无数据').or(locator('ul.divide-y'))

```

# Page snapshot

```yaml
- generic [active] [ref=e1]:
  - generic [ref=e2]:
    - generic [ref=e3]:
      - complementary [ref=e4]:
        - generic [ref=e6]: Cuckoo-Echo
        - navigation "管理后台导航" [ref=e7]:
          - link "数据看板" [ref=e8] [cursor=pointer]:
            - /url: /admin/metrics
          - link "知识库管理" [ref=e9] [cursor=pointer]:
            - /url: /admin/knowledge
          - link "人工介入" [ref=e10] [cursor=pointer]:
            - /url: /admin/hitl
          - link "配置中心" [ref=e11] [cursor=pointer]:
            - /url: /admin/config
          - link "沙盒测试" [ref=e12] [cursor=pointer]:
            - /url: /admin/sandbox
      - generic [ref=e13]:
        - banner [ref=e14]:
          - generic [ref=e15]:
            - generic [ref=e16]:
              - text: 3a8b393c-c7ef-4df2-9610-6c57949d0d10
              - generic [ref=e17]: (00000000-0000-4000-a000-000000000001)
            - button "退出登录" [ref=e18]
        - main [ref=e19]:
          - generic [ref=e20]:
            - generic [ref=e21]:
              - heading "数据看板" [level=1] [ref=e22]
              - button "刷新数据" [ref=e23]: 刷新
            - group "时间范围选择" [ref=e24]:
              - button "最近 1 天" [ref=e25]
              - button "最近 7 天" [pressed] [ref=e26]
              - button "最近 30 天" [ref=e27]
            - generic [ref=e28]:
              - generic [ref=e29]:
                - paragraph [ref=e30]: 总对话数
                - paragraph [ref=e31]: "0"
              - generic [ref=e32]:
                - paragraph [ref=e33]: 转人工次数
                - paragraph [ref=e34]: NaN
              - generic [ref=e35]:
                - paragraph [ref=e36]: 转人工率
                - paragraph [ref=e37]: NaN%
            - generic [ref=e38]:
              - generic [ref=e39]:
                - paragraph [ref=e40]: 总 Token 数
                - paragraph [ref=e41]: "0"
              - generic [ref=e42]:
                - paragraph [ref=e43]: 消息数量
                - paragraph [ref=e44]: "0"
                - paragraph [ref=e45]: (基于对话数)
              - generic [ref=e46]:
                - paragraph [ref=e47]: 用户满意度 (👍)
                - paragraph [ref=e48]: "--%"
            - generic [ref=e49]:
              - generic [ref=e50]:
                - heading "Token 消耗趋势" [level=2] [ref=e51]
                - application [ref=e54]:
                  - generic [ref=e66]:
                    - generic [ref=e67]:
                      - generic [ref=e69]: 3/30
                      - generic [ref=e71]: 3/31
                      - generic [ref=e73]: 4/1
                      - generic [ref=e75]: 4/2
                      - generic [ref=e77]: 4/3
                      - generic [ref=e79]: 4/4
                      - generic [ref=e81]: 4/5
                    - generic [ref=e82]:
                      - generic [ref=e84]: "0"
                      - generic [ref=e86]: "1"
                      - generic [ref=e88]: "2"
                      - generic [ref=e90]: "3"
                      - generic [ref=e92]: "4"
              - generic [ref=e93]:
                - heading "对话数分布" [level=2] [ref=e94]
                - application [ref=e97]:
                  - generic [ref=e109]:
                    - generic [ref=e110]:
                      - generic [ref=e112]: 3/30
                      - generic [ref=e114]: 3/31
                      - generic [ref=e116]: 4/1
                      - generic [ref=e118]: 4/2
                      - generic [ref=e120]: 4/3
                      - generic [ref=e122]: 4/4
                      - generic [ref=e124]: 4/5
                    - generic [ref=e125]:
                      - generic [ref=e127]: "0"
                      - generic [ref=e129]: "1"
                      - generic [ref=e131]: "2"
                      - generic [ref=e133]: "3"
                      - generic [ref=e135]: "4"
            - generic [ref=e136]:
              - heading "高频未命中问题" [level=2] [ref=e137]
              - paragraph [ref=e138]: 暂无数据
    - region "Notifications (F8)":
      - list "通知列表"
  - generic [ref=e139]: "0"
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  | 
  3  | /**
  4  |  * Integration test: Metrics Dashboard against real backend.
  5  |  * Seed credentials: admin@test.com / test123456
  6  |  */
  7  | 
  8  | async function loginAsAdmin(page: import('@playwright/test').Page) {
  9  |   await page.goto('/login');
  10 |   await page.fill('input[aria-label="邮箱"]', 'admin@test.com');
  11 |   await page.fill('input[aria-label="密码"]', 'test123456');
  12 |   await page.click('button[aria-label="登录"]');
  13 |   await expect(page).toHaveURL(/\/admin\/metrics/, { timeout: 10_000 });
  14 | }
  15 | 
  16 | test.describe('Metrics Dashboard (integration)', () => {
  17 |   test('dashboard renders metric cards after login', async ({ page }) => {
  18 |     await loginAsAdmin(page);
  19 | 
  20 |     await expect(page.locator('h1:has-text("数据看板")')).toBeVisible();
  21 |     await expect(page.locator('text=总对话数')).toBeVisible();
  22 |     await expect(page.locator('text=总 Token 数')).toBeVisible();
  23 |   });
  24 | 
  25 |   test('period selector changes active state', async ({ page }) => {
  26 |     await loginAsAdmin(page);
  27 | 
  28 |     // Default is 7d
  29 |     const btn7d = page.locator('button:has-text("最近 7 天")');
  30 |     await expect(btn7d).toHaveAttribute('aria-pressed', 'true');
  31 | 
  32 |     // Click 1d
  33 |     const btn1d = page.locator('button:has-text("最近 1 天")');
  34 |     await btn1d.click();
  35 |     await expect(btn1d).toHaveAttribute('aria-pressed', 'true');
  36 |     await expect(btn7d).toHaveAttribute('aria-pressed', 'false');
  37 | 
  38 |     // Click 30d
  39 |     const btn30d = page.locator('button:has-text("最近 30 天")');
  40 |     await btn30d.click();
  41 |     await expect(btn30d).toHaveAttribute('aria-pressed', 'true');
  42 |   });
  43 | 
  44 |   test('refresh button triggers data reload', async ({ page }) => {
  45 |     await loginAsAdmin(page);
  46 | 
  47 |     const refreshBtn = page.locator('button[aria-label="刷新数据"]');
  48 |     await expect(refreshBtn).toBeVisible();
  49 |     await refreshBtn.click();
  50 | 
  51 |     // Button should show loading state briefly
  52 |     await expect(refreshBtn).toBeVisible();
  53 |   });
  54 | 
  55 |   test('charts are rendered', async ({ page }) => {
  56 |     await loginAsAdmin(page);
  57 | 
  58 |     await expect(page.locator('h2:has-text("Token 消耗趋势")')).toBeVisible();
  59 |     await expect(page.locator('h2:has-text("对话数分布")')).toBeVisible();
  60 |   });
  61 | 
  62 |   test('missed queries section is visible', async ({ page }) => {
  63 |     await loginAsAdmin(page);
  64 | 
  65 |     await expect(page.locator('h2:has-text("高频未命中问题")')).toBeVisible();
  66 |     // Either data or empty state
  67 |     const data = page.locator('text=暂无数据');
  68 |     const list = page.locator('ul.divide-y');
> 69 |     await expect(data.or(list)).toBeVisible({ timeout: 5_000 });
     |                                 ^ Error: expect(locator).toBeVisible() failed
  70 |   });
  71 | 
  72 |   test('metrics API returns data', async ({ page, request }) => {
  73 |     // Login first to get a token
  74 |     await loginAsAdmin(page);
  75 | 
  76 |     // Intercept a metrics API call
  77 |     const metricsPromise = page.waitForResponse(
  78 |       (resp) => resp.url().includes('/admin/v1/metrics/overview'),
  79 |     );
  80 | 
  81 |     await page.locator('button[aria-label="刷新数据"]').click();
  82 |     const response = await metricsPromise.catch(() => null);
  83 |     if (response) {
  84 |       expect(response.status()).toBe(200);
  85 |     }
  86 |   });
  87 | });
  88 | 
```