// Feature: frontend-ui, Property 5: 错误状态码映射完整性
// **Validates: Requirements 11.1, 11.2, 11.3, 11.6**

import fc from 'fast-check';
import { ERROR_MAP } from '../../lib/errorMap';

const KNOWN_STATUS_CODES = [401, 409, 415, 429, 500, 503] as const;

/**
 * Patterns that indicate technical details leaking into user-facing messages.
 * These should NEVER appear in error messages shown to users.
 */
const TECHNICAL_PATTERNS = [
  /stack\s*trace/i,
  /at\s+\w+\s*\(/,           // stack frame like "at Function ("
  /\{[\s\S]*"error"/,         // JSON error body
  /https?:\/\//,              // URL paths
  /\/api\//,                  // API paths
  /\/v\d+\//,                 // versioned API paths
  /Error:\s/,                 // Error: prefix
  /Exception/i,
  /Traceback/i,
  /\.ts:\d+/,                 // TypeScript file references
  /\.js:\d+/,                 // JavaScript file references
  /node_modules/,
];

describe('Property 5: 错误状态码映射完整性', () => {
  it('ERROR_MAP[statusCode] returns a non-empty string for all known status codes', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...KNOWN_STATUS_CODES),
        (statusCode) => {
          const message = ERROR_MAP[statusCode];

          // Must be defined and non-empty
          expect(message).toBeDefined();
          expect(typeof message).toBe('string');
          expect(message.length).toBeGreaterThan(0);
        },
      ),
      { numRuns: 100 },
    );
  });

  it('error messages do NOT contain technical details', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...KNOWN_STATUS_CODES),
        (statusCode) => {
          const message = ERROR_MAP[statusCode];

          for (const pattern of TECHNICAL_PATTERNS) {
            expect(message).not.toMatch(pattern);
          }
        },
      ),
      { numRuns: 100 },
    );
  });
});
