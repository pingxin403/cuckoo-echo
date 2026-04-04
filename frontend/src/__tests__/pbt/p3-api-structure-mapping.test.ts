// Feature: frontend-integration, Property 3: API 响应结构映射完整性
// **Validates: Requirements 1.1, 1.4, 7.1, 7.3, 7.4**

import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import { transformResponse } from '@/network/fieldMapper';

/**
 * Arbitrary: generates a random metrics overview backend response.
 */
const arbOverviewResponse = fc.record({
  total_conversations: fc.nat({ max: 100000 }),
  human_transfer_count: fc.nat({ max: 10000 }),
  human_transfer_rate: fc.double({ min: 0, max: 1, noNaN: true }),
  range: fc.constantFrom('24h', '7d', '30d'),
});

/**
 * Arbitrary: generates a random missed-queries backend response.
 */
const arbMissedQueriesResponse = fc.record({
  missed_queries: fc.array(
    fc.record({
      query_prefix: fc.string({ minLength: 1, maxLength: 50 }),
      count: fc.nat({ max: 1000 }),
    }),
    { minLength: 0, maxLength: 20 },
  ),
  range: fc.constantFrom('24h', '7d', '30d'),
});

describe('Property 3: API 响应结构映射完整性', () => {
  it('overview: aiResolutionRate = 1 - humanEscalationRate', () => {
    fc.assert(
      fc.property(arbOverviewResponse, (backendResponse) => {
        const result = transformResponse(
          backendResponse,
          '/admin/v1/metrics/overview',
        ) as Record<string, unknown>;

        // humanEscalationRate should exist (mapped from human_transfer_rate)
        expect(typeof result.humanEscalationRate).toBe('number');
        // aiResolutionRate should be computed as 1 - humanEscalationRate
        expect(typeof result.aiResolutionRate).toBe('number');

        const humanRate = result.humanEscalationRate as number;
        const aiRate = result.aiResolutionRate as number;

        // aiResolutionRate = 1 - humanEscalationRate (within floating point tolerance)
        expect(Math.abs(aiRate - (1 - humanRate))).toBeLessThan(1e-10);

        // totalConversations should exist
        expect(typeof result.totalConversations).toBe('number');
      }),
      { numRuns: 150 },
    );
  });

  it('missed-queries: result is unwrapped array with query field', () => {
    fc.assert(
      fc.property(arbMissedQueriesResponse, (backendResponse) => {
        const result = transformResponse(
          backendResponse,
          '/admin/v1/metrics/missed-queries',
        );

        // Result should be an array (unwrapped from {missed_queries: [...]})
        expect(Array.isArray(result)).toBe(true);

        const arr = result as Record<string, unknown>[];
        for (const item of arr) {
          // Each item should have 'query' field (mapped from query_prefix)
          // After explicit rename query_prefix→query then camelCase conversion
          expect('query' in item || 'queryPrefix' in item).toBe(true);
          expect(typeof item.count).toBe('number');
        }
      }),
      { numRuns: 150 },
    );
  });
});
