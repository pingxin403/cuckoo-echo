// Feature: frontend-integration, Property 5: 实时消息格式转换完整性
// **Validates: Requirements 4.5, 5.3**

import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import {
  convertLangGraphMessage,
  type LangGraphMessage,
} from '@/lib/langGraphAdapter';

/**
 * Arbitrary: generates a random LangGraph message (human or ai type).
 */
const arbLangGraphMessage: fc.Arbitrary<LangGraphMessage> = fc.record({
  type: fc.constantFrom('human' as const, 'ai' as const),
  content: fc.string({ minLength: 0, maxLength: 200 }),
  id: fc.option(fc.uuid(), { nil: undefined }),
});

/**
 * Arbitrary: generates a random threadId.
 */
const arbThreadId = fc.uuid();

describe('Property 5: 实时消息格式转换完整性', () => {
  it('role mapping: human→user, ai→assistant; content preserved; id/threadId/createdAt non-empty', () => {
    fc.assert(
      fc.property(
        arbLangGraphMessage,
        arbThreadId,
        (langMsg, threadId) => {
          const message = convertLangGraphMessage(langMsg, threadId);

          // Role mapping correctness
          if (langMsg.type === 'human') {
            expect(message.role).toBe('user');
          } else if (langMsg.type === 'ai') {
            expect(message.role).toBe('assistant');
          }

          // Content preservation
          expect(message.content).toBe(langMsg.content);

          // id must be non-empty string
          expect(typeof message.id).toBe('string');
          expect(message.id.length).toBeGreaterThan(0);

          // threadId must match input
          expect(message.threadId).toBe(threadId);

          // createdAt must be non-empty ISO string
          expect(typeof message.createdAt).toBe('string');
          expect(message.createdAt.length).toBeGreaterThan(0);
          // Validate it's a parseable date
          expect(Number.isNaN(Date.parse(message.createdAt))).toBe(false);
        },
      ),
      { numRuns: 150 },
    );
  });

  it('when LangGraph message has an id, it is preserved in the output', () => {
    fc.assert(
      fc.property(
        fc.record({
          type: fc.constantFrom('human' as const, 'ai' as const),
          content: fc.string({ minLength: 1, maxLength: 50 }),
          id: fc.uuid(),
        }),
        arbThreadId,
        (langMsg, threadId) => {
          const message = convertLangGraphMessage(langMsg, threadId);
          expect(message.id).toBe(langMsg.id);
        },
      ),
      { numRuns: 100 },
    );
  });
});
