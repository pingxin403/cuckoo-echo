import { describe, it, expect } from 'vitest';
import {
  convertLangGraphMessage,
  convertLangGraphMessages,
  type LangGraphMessage,
} from '@/lib/langGraphAdapter';

describe('langGraphAdapter', () => {
  const threadId = 'test-thread-123';

  describe('convertLangGraphMessage', () => {
    it('converts human message to user role', () => {
      const msg: LangGraphMessage = { type: 'human', content: 'Hello' };
      const result = convertLangGraphMessage(msg, threadId);
      expect(result.role).toBe('user');
      expect(result.content).toBe('Hello');
      expect(result.threadId).toBe(threadId);
    });

    it('converts ai message to assistant role', () => {
      const msg: LangGraphMessage = { type: 'ai', content: 'Hi there' };
      const result = convertLangGraphMessage(msg, threadId);
      expect(result.role).toBe('assistant');
      expect(result.content).toBe('Hi there');
    });

    it('preserves message id when provided', () => {
      const msg: LangGraphMessage = { type: 'human', content: 'test', id: 'msg-001' };
      const result = convertLangGraphMessage(msg, threadId);
      expect(result.id).toBe('msg-001');
    });

    it('generates id when not provided', () => {
      const msg: LangGraphMessage = { type: 'human', content: 'test' };
      const result = convertLangGraphMessage(msg, threadId);
      expect(result.id).toBeTruthy();
      expect(result.id.length).toBeGreaterThan(0);
    });

    it('converts tool_calls to toolCalls format', () => {
      const msg: LangGraphMessage = {
        type: 'ai',
        content: '',
        tool_calls: [
          { id: 'tc-1', name: 'get_order', args: { order_id: '123' } },
        ],
      };
      const result = convertLangGraphMessage(msg, threadId);
      expect(result.toolCalls).toHaveLength(1);
      expect(result.toolCalls![0].name).toBe('get_order');
      expect(result.toolCalls![0].arguments).toBe('{"order_id":"123"}');
    });

    it('defaults unknown type to assistant role', () => {
      const msg: LangGraphMessage = { type: 'tool', content: 'result' };
      const result = convertLangGraphMessage(msg, threadId);
      expect(result.role).toBe('assistant');
    });

    it('sets createdAt to a valid ISO string', () => {
      const msg: LangGraphMessage = { type: 'human', content: 'test' };
      const result = convertLangGraphMessage(msg, threadId);
      expect(() => new Date(result.createdAt)).not.toThrow();
    });
  });

  describe('convertLangGraphMessages', () => {
    it('converts array of messages', () => {
      const msgs: LangGraphMessage[] = [
        { type: 'human', content: 'Hello' },
        { type: 'ai', content: 'Hi' },
      ];
      const result = convertLangGraphMessages(msgs, threadId);
      expect(result).toHaveLength(2);
      expect(result[0].role).toBe('user');
      expect(result[1].role).toBe('assistant');
    });

    it('filters out tool messages', () => {
      const msgs: LangGraphMessage[] = [
        { type: 'human', content: 'Check order' },
        { type: 'ai', content: '', tool_calls: [{ id: '1', name: 'get_order', args: {} }] },
        { type: 'tool', content: '{"status":"shipped"}' },
        { type: 'ai', content: 'Your order has been shipped.' },
      ];
      const result = convertLangGraphMessages(msgs, threadId);
      expect(result).toHaveLength(3); // tool message filtered
      expect(result.map((m) => m.role)).toEqual(['user', 'assistant', 'assistant']);
    });

    it('handles empty array', () => {
      const result = convertLangGraphMessages([], threadId);
      expect(result).toEqual([]);
    });
  });
});
