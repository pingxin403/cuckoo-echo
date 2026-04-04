// Feature: frontend-ui, Property 7: 消息 Reconciliation 合并正确性
// **Validates: Requirements 1.6**

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

const ROLES = ['user', 'assistant', 'human_agent'] as const;

/**
 * Arbitrary: generates a confirmed (non-optimistic) server message.
 */
function arbServerMessage(idPrefix: string): fc.Arbitrary<Message> {
  return fc.record({
    id: fc.uuid().map((u) => `${idPrefix}_${u}`),
    threadId: fc.constant('thread_test'),
    role: fc.constantFrom(...ROLES),
    content: fc.string({ minLength: 1, maxLength: 100 }),
    createdAt: fc
      .integer({
        min: new Date('2020-01-01').getTime(),
        max: new Date('2030-01-01').getTime(),
      })
      .map((ts) => new Date(ts).toISOString()),
    isOptimistic: fc.constant(false),
  });
}

/**
 * Arbitrary: generates an optimistic (unconfirmed) local message with temp_ prefix.
 */
function arbOptimisticMessage(): fc.Arbitrary<Message> {
  return fc.record({
    id: fc.uuid().map((u) => `temp_${u}`),
    threadId: fc.constant('thread_test'),
    role: fc.constant('user' as const),
    content: fc.string({ minLength: 1, maxLength: 100 }),
    createdAt: fc
      .integer({
        min: new Date('2020-01-01').getTime(),
        max: new Date('2030-01-01').getTime(),
      })
      .map((ts) => new Date(ts).toISOString()),
    isOptimistic: fc.constant(true),
  });
}

/**
 * Arbitrary: generates a test scenario with local messages (mix of confirmed + optimistic)
 * and server messages (some overlapping with local confirmed messages).
 */
const arbReconcileScenario = fc
  .record({
    // Server messages: 1–30
    serverMessages: fc.array(arbServerMessage('srv'), { minLength: 1, maxLength: 30 }),
    // Local optimistic messages: 0–10
    localOptimistic: fc.array(arbOptimisticMessage(), { minLength: 0, maxLength: 10 }),
  })
  .chain(({ serverMessages, localOptimistic }) => {
    // Pick a random subset of server messages to also appear in local (simulating overlap)
    return fc
      .subarray(serverMessages, { minLength: 0 })
      .map((overlapping) => ({
        serverMessages,
        localMessages: [...overlapping, ...localOptimistic],
      }));
  });

describe('Property 7: 消息 Reconciliation 合并正确性', () => {
  it('reconcileMessages satisfies all 4 invariants', () => {
    fc.assert(
      fc.property(arbReconcileScenario, ({ serverMessages, localMessages }) => {
        // Set local messages in store
        useChatStore.setState({ messages: localMessages });

        // Call reconcileMessages
        useChatStore.getState().reconcileMessages(serverMessages);

        const result = useChatStore.getState().messages;
        const resultIds = result.map((m) => m.id);

        // (1) All server messages are present in the result
        for (const sm of serverMessages) {
          expect(resultIds).toContain(sm.id);
        }

        // (2) Unconfirmed optimistic messages (not in server IDs) are preserved
        const serverIdSet = new Set(serverMessages.map((m) => m.id));
        const unconfirmedOptimistic = localMessages.filter(
          (m) => m.isOptimistic && !serverIdSet.has(m.id),
        );
        for (const om of unconfirmedOptimistic) {
          expect(resultIds).toContain(om.id);
        }

        // (3) Result is sorted by createdAt ascending
        for (let i = 1; i < result.length; i++) {
          const prevTime = new Date(result[i - 1].createdAt).getTime();
          const currTime = new Date(result[i].createdAt).getTime();
          expect(currTime).toBeGreaterThanOrEqual(prevTime);
        }

        // (4) No duplicate IDs
        const uniqueIds = new Set(resultIds);
        expect(uniqueIds.size).toBe(result.length);
      }),
      { numRuns: 150 },
    );
  });
});
