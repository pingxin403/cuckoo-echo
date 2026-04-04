// Feature: frontend-integration, Property 2: SSE 双格式解析完整性
// **Validates: Requirements 4.2**

import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import { extractTokenContent } from '@/network/sseClient';

/**
 * Arbitrary: generates a random token string including Chinese, English, and special chars.
 */
const arbToken: fc.Arbitrary<string> = fc.oneof(
  fc.string({ minLength: 1, maxLength: 30 }),
  // Chinese characters
  fc
    .array(
      fc.integer({ min: 0x4e00, max: 0x9fff }).map((cp) => String.fromCodePoint(cp)),
      { minLength: 1, maxLength: 10 },
    )
    .map((chars) => chars.join('')),
  // Special characters and mixed content
  fc.constantFrom(
    'hello world',
    '你好世界',
    '**bold**',
    '`code`',
    '<tag>',
    '&amp;',
    '😀🎉',
    'café',
    'naïve',
    'a b\tc',
  ),
);

/**
 * Arbitrary: generates a token sequence of 1–200 tokens.
 */
const arbTokenSequence: fc.Arbitrary<string[]> = fc.array(arbToken, {
  minLength: 1,
  maxLength: 200,
});

/**
 * Arbitrary: for each token, randomly choose backend or OpenAI format encoding.
 */
function encodeToken(
  token: string,
  useBackendFormat: boolean,
): Record<string, unknown> {
  if (useBackendFormat) {
    return { content: token };
  }
  return { choices: [{ delta: { content: token } }] };
}

describe('Property 2: SSE 双格式解析完整性', () => {
  it('extractTokenContent correctly extracts tokens from both backend and OpenAI formats', () => {
    fc.assert(
      fc.property(
        arbTokenSequence,
        fc.array(fc.boolean(), { minLength: 1, maxLength: 200 }),
        (tokens, formatFlags) => {
          for (let i = 0; i < tokens.length; i++) {
            const token = tokens[i];
            const useBackend = formatFlags[i % formatFlags.length];
            const encoded = encodeToken(token, useBackend);
            const extracted = extractTokenContent(
              encoded as Record<string, unknown>,
            );
            expect(extracted).toBe(token);
          }
        },
      ),
      { numRuns: 150 },
    );
  });

  it('concatenation of extracted tokens matches original token sequence', () => {
    fc.assert(
      fc.property(
        arbTokenSequence,
        fc.array(fc.boolean(), { minLength: 1, maxLength: 200 }),
        (tokens, formatFlags) => {
          const extracted: string[] = [];
          for (let i = 0; i < tokens.length; i++) {
            const token = tokens[i];
            const useBackend = formatFlags[i % formatFlags.length];
            const encoded = encodeToken(token, useBackend);
            const content = extractTokenContent(
              encoded as Record<string, unknown>,
            );
            if (content !== undefined) {
              extracted.push(content);
            }
          }
          expect(extracted.join('')).toBe(tokens.join(''));
        },
      ),
      { numRuns: 150 },
    );
  });
});
