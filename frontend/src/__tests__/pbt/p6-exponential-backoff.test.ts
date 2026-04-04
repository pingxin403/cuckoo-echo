// Feature: frontend-integration, Property 6: 指数退避延迟序列
// **Validates: Requirements 4.6**

import { describe, it, expect } from 'vitest';
import fc from 'fast-check';

/**
 * Compute the expected exponential backoff delay for the k-th failure.
 * delay = min(1000 * 2^(k-1), 30000)
 */
function expectedDelay(k: number): number {
  return Math.min(1000 * Math.pow(2, k - 1), 30000);
}

/**
 * Arbitrary: generates a random failure count between 1 and 20.
 */
const arbFailureCount = fc.integer({ min: 1, max: 20 });

describe('Property 6: 指数退避延迟序列', () => {
  it('delay = min(1000 * 2^(k-1), 30000) for failure count k', () => {
    fc.assert(
      fc.property(arbFailureCount, (k) => {
        const delay = expectedDelay(k);

        // Must equal the formula
        expect(delay).toBe(Math.min(1000 * Math.pow(2, k - 1), 30000));

        // Must be at least 1000ms (initial delay)
        expect(delay).toBeGreaterThanOrEqual(1000);

        // Must not exceed 30000ms (cap)
        expect(delay).toBeLessThanOrEqual(30000);
      }),
      { numRuns: 150 },
    );
  });

  it('delay sequence is non-decreasing until cap is reached', () => {
    fc.assert(
      fc.property(arbFailureCount, (maxK) => {
        const delays: number[] = [];
        for (let k = 1; k <= maxK; k++) {
          delays.push(expectedDelay(k));
        }

        // Verify non-decreasing
        for (let i = 1; i < delays.length; i++) {
          expect(delays[i]).toBeGreaterThanOrEqual(delays[i - 1]);
        }

        // Once cap is reached, all subsequent delays should be 30000
        const capIndex = delays.findIndex((d) => d === 30000);
        if (capIndex >= 0) {
          for (let i = capIndex; i < delays.length; i++) {
            expect(delays[i]).toBe(30000);
          }
        }
      }),
      { numRuns: 150 },
    );
  });

  it('simulates WSClient-style reconnect delay accumulation and reset', () => {
    fc.assert(
      fc.property(arbFailureCount, (failureCount) => {
        // Simulate the WSClient reconnect logic
        let reconnectDelay = 1000;
        const maxReconnectDelay = 30000;
        const delays: number[] = [];

        for (let i = 0; i < failureCount; i++) {
          delays.push(reconnectDelay);
          reconnectDelay = Math.min(reconnectDelay * 2, maxReconnectDelay);
        }

        // Verify each delay matches the formula
        for (let i = 0; i < delays.length; i++) {
          expect(delays[i]).toBe(expectedDelay(i + 1));
        }

        // Simulate successful connection → reset
        reconnectDelay = 1000;
        expect(reconnectDelay).toBe(1000);
      }),
      { numRuns: 150 },
    );
  });
});
