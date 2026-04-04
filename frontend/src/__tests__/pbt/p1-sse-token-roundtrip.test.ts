// Feature: frontend-ui, Property 1: SSE Token 流渲染完整性（Round-Trip）
// **Validates: Requirements 1.1, 1.2**

import { describe, it, expect, beforeEach } from 'vitest';
import fc from 'fast-check';
import { useChatStore } from '@/stores/chatStore';

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
 * Arbitrary: generates a single SSE token string.
 * Includes Chinese, English, Markdown syntax, special characters, whitespace.
 */
const arbToken: fc.Arbitrary<string> = fc.oneof(
  // Plain English words
  fc.string({ minLength: 1, maxLength: 20 }),
  // Chinese characters
  fc
    .array(
      fc.integer({ min: 0x4e00, max: 0x9fff }).map((cp) => String.fromCodePoint(cp)),
      { minLength: 1, maxLength: 10 },
    )
    .map((chars) => chars.join('')),
  // Markdown syntax fragments
  fc.constantFrom(
    '**bold**',
    '*italic*',
    '`code`',
    '```\n',
    '\n```',
    '# Heading',
    '## H2',
    '- list item',
    '1. ordered',
    '[link](https://example.com)',
    '![img](https://example.com/img.png)',
    '> blockquote',
    '---',
    '| col |',
    '\n',
    ' ',
  ),
  // Special characters
  fc.constantFrom(
    '&amp;', '<', '>', '"', "'", '\\', '/', '\t', '\r\n',
    '😀', '🎉', '中文测试', '日本語', '한국어',
  ),
);

/**
 * Arbitrary: generates a token sequence of 1–500 tokens.
 */
const arbTokenSequence: fc.Arbitrary<string[]> = fc.array(arbToken, {
  minLength: 1,
  maxLength: 500,
});

describe('Property 1: SSE Token 流渲染完整性（Round-Trip）', () => {
  it('streamingContent equals concatenation of all appended tokens', () => {
    fc.assert(
      fc.property(arbTokenSequence, (tokens) => {
        // Reset streaming state
        useChatStore.setState({ streamingContent: '', isStreaming: true });

        // Simulate SSE flow: append each token to the store
        for (const token of tokens) {
          useChatStore.getState().appendToken(token);
        }

        // The expected result is the simple concatenation of all tokens
        const expected = tokens.join('');
        const actual = useChatStore.getState().streamingContent;

        // Assert round-trip: streamingContent === concat(t1, t2, ..., tn)
        expect(actual).toBe(expected);
      }),
      { numRuns: 150 },
    );
  });
});
