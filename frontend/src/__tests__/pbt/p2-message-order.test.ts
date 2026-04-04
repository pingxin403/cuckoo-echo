// Feature: frontend-ui, Property 2: 消息顺序不变量
// **Validates: Requirements 1.8, 3.2**

import { describe, it, expect, beforeEach } from 'vitest';
import fc from 'fast-check';
import { useChatStore } from '@/stores/chatStore';
import type { Message } from '@/types';

// Reset store state before each test
beforeEach(() => {
  useChatStore.setState({
    messages: [],
    activeThreadId: null,
    isStreaming: false,
    streamingContent: '',
    connectionStatus: 'disconnected',
    error: null,
  });
});

/**
 * Arbitrary: generates a random Message with a random createdAt timestamp.
 * Timestamps range from 2020-01-01 to 2030-01-01.
 */
const arbMessage: fc.Arbitrary<Message> = fc
  .record({
    id: fc.uuid(),
    threadId: fc.constant('thread_test'),
    role: fc.constantFrom('user' as const, 'assistant' as const, 'human_agent' as const),
    content: fc.string({ minLength: 1, maxLength: 200 }),
    createdAt: fc
      .integer({
        min: new Date('2020-01-01').getTime(),
        max: new Date('2030-01-01').getTime(),
      })
      .map((ts) => new Date(ts).toISOString()),
  });

/**
 * Arbitrary: generates an array of 1–100 random messages with unique IDs.
 */
const arbMessages: fc.Arbitrary<Message[]> = fc
  .array(arbMessage, { minLength: 1, maxLength: 100 })
  // Ensure unique IDs by appending index
  .map((msgs) =>
    msgs.map((m, i) => ({ ...m, id: `${m.id}_${i}` })),
  );

describe('Property 2: 消息顺序不变量', () => {
  it('messages are sorted by createdAt ascending after reconcileMessages', () => {
    fc.assert(
      fc.property(arbMessages, (messages) => {
        // Set messages in store (unsorted)
        useChatStore.setState({ messages: [] });

        // Call reconcileMessages with the random messages — this triggers sorting
        useChatStore.getState().reconcileMessages(messages);

        const result = useChatStore.getState().messages;

        // Assert: messages are sorted by createdAt ascending
        for (let i = 1; i < result.length; i++) {
          const prevTime = new Date(result[i - 1].createdAt).getTime();
          const currTime = new Date(result[i].createdAt).getTime();
          expect(currTime).toBeGreaterThanOrEqual(prevTime);
        }
      }),
      { numRuns: 150 },
    );
  });
});
