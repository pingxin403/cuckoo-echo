import { defineConfig } from '@playwright/test';

/**
 * Playwright config for integration tests against real backend services.
 * Runs against Docker Compose stack (http://localhost).
 * Does NOT start Vite dev server — expects services already running.
 */
export default defineConfig({
  testDir: './e2e',
  testMatch: '**/*.integration.spec.ts',
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost',
    extraHTTPHeaders: {
      'X-Test-Mode': 'integration',
    },
  },
  webServer: undefined,
  retries: 1,
  timeout: 60_000,
});
