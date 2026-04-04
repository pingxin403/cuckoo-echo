import { describe, it, expect, beforeEach } from 'vitest';
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

describe('chatStore', () => {
  describe('sendMessage', () => {
    it('adds an optimistic message with temp_id and sets isStreaming=true', () => {
      useChatStore.setState({ activeThreadId: 'thread_1' });

      useChatStore.getState().sendMessage('Hello world');

      const state = useChatStore.getState();
      expect(state.isStreaming).toBe(true);
      expect(state.messages).toHaveLength(1);

      const msg = state.messages[0];
      expect(msg.id).toMatch(/^temp_/);
      expect(msg.content).toBe('Hello world');
      expect(msg.role).toBe('user');
      expect(msg.threadId).toBe('thread_1');
      expect(msg.isOptimistic).toBe(true);
      expect(msg.createdAt).toBeTruthy();
    });

    it('includes media attachments when provided', () => {
      useChatStore.setState({ activeThreadId: 'thread_1' });
      const media = [{ type: 'image' as const, url: 'https://img.test/a.png', mimeType: 'image/png', sizeKb: 200 }];

      useChatStore.getState().sendMessage('Check this', media);

      const msg = useChatStore.getState().messages[0];
      expect(msg.mediaAttachments).toEqual(media);
    });
  });

  describe('appendToken', () => {
    it('accumulates streamingContent', () => {
      useChatStore.getState().appendToken('Hello');
      expect(useChatStore.getState().streamingContent).toBe('Hello');

      useChatStore.getState().appendToken(' world');
      expect(useChatStore.getState().streamingContent).toBe('Hello world');
    });
  });

  describe('finishStreaming', () => {
    it('clears streaming state and updates message content', () => {
      const msg: Message = {
        id: 'msg_1',
        threadId: 'thread_1',
        role: 'assistant',
        content: '',
        createdAt: '2024-01-01T00:00:00Z',
      };
      useChatStore.setState({
        messages: [msg],
        isStreaming: true,
        streamingContent: 'Streamed content here',
      });

      useChatStore.getState().finishStreaming('msg_1');

      const state = useChatStore.getState();
      expect(state.isStreaming).toBe(false);
      expect(state.streamingContent).toBe('');
      expect(state.messages[0].content).toBe('Streamed content here');
    });

    it('keeps original content if streamingContent is empty', () => {
      const msg: Message = {
        id: 'msg_1',
        threadId: 'thread_1',
        role: 'assistant',
        content: 'Original content',
        createdAt: '2024-01-01T00:00:00Z',
      };
      useChatStore.setState({
        messages: [msg],
        isStreaming: true,
        streamingContent: '',
      });

      useChatStore.getState().finishStreaming('msg_1');

      expect(useChatStore.getState().messages[0].content).toBe('Original content');
    });
  });

  describe('replaceTempId', () => {
    it('swaps temp_id for real id and clears isOptimistic', () => {
      const msg: Message = {
        id: 'temp_abc123',
        threadId: 'thread_1',
        role: 'user',
        content: 'Hello',
        createdAt: '2024-01-01T00:00:00Z',
        isOptimistic: true,
      };
      useChatStore.setState({ messages: [msg] });

      useChatStore.getState().replaceTempId('temp_abc123', 'msg_real_001');

      const updated = useChatStore.getState().messages[0];
      expect(updated.id).toBe('msg_real_001');
      expect(updated.isOptimistic).toBe(false);
    });

    it('does not affect other messages', () => {
      const msgs: Message[] = [
        { id: 'temp_1', threadId: 't', role: 'user', content: 'A', createdAt: '2024-01-01T00:00:00Z', isOptimistic: true },
        { id: 'msg_2', threadId: 't', role: 'assistant', content: 'B', createdAt: '2024-01-01T00:00:01Z' },
      ];
      useChatStore.setState({ messages: msgs });

      useChatStore.getState().replaceTempId('temp_1', 'msg_real_1');

      const state = useChatStore.getState();
      expect(state.messages[0].id).toBe('msg_real_1');
      expect(state.messages[1].id).toBe('msg_2');
    });
  });

  describe('reconcileMessages', () => {
    it('merges server + local, keeps unconfirmed optimistic, sorts by createdAt, deduplicates', () => {
      const localMsgs: Message[] = [
        { id: 'msg_1', threadId: 't', role: 'user', content: 'A', createdAt: '2024-01-01T00:00:00Z' },
        { id: 'temp_2', threadId: 't', role: 'user', content: 'B', createdAt: '2024-01-01T00:00:05Z', isOptimistic: true },
      ];
      const serverMsgs: Message[] = [
        { id: 'msg_1', threadId: 't', role: 'user', content: 'A', createdAt: '2024-01-01T00:00:00Z' },
        { id: 'msg_3', threadId: 't', role: 'assistant', content: 'C', createdAt: '2024-01-01T00:00:02Z' },
      ];
      useChatStore.setState({ messages: localMsgs });

      useChatStore.getState().reconcileMessages(serverMsgs);

      const result = useChatStore.getState().messages;
      // Should contain all server msgs + unconfirmed optimistic (temp_2)
      expect(result).toHaveLength(3);
      // Sorted by createdAt ascending
      expect(result[0].id).toBe('msg_1');
      expect(result[1].id).toBe('msg_3');
      expect(result[2].id).toBe('temp_2');
    });

    it('does not keep optimistic messages that server has acknowledged', () => {
      const localMsgs: Message[] = [
        { id: 'temp_1', threadId: 't', role: 'user', content: 'A', createdAt: '2024-01-01T00:00:00Z', isOptimistic: true },
      ];
      const serverMsgs: Message[] = [
        { id: 'temp_1', threadId: 't', role: 'user', content: 'A', createdAt: '2024-01-01T00:00:00Z' },
      ];
      useChatStore.setState({ messages: localMsgs });

      useChatStore.getState().reconcileMessages(serverMsgs);

      const result = useChatStore.getState().messages;
      // Server acknowledged temp_1, so only 1 copy
      expect(result).toHaveLength(1);
      expect(result[0].id).toBe('temp_1');
    });

    it('deduplicates messages with the same id', () => {
      const serverMsgs: Message[] = [
        { id: 'msg_1', threadId: 't', role: 'user', content: 'A', createdAt: '2024-01-01T00:00:00Z' },
        { id: 'msg_1', threadId: 't', role: 'user', content: 'A duplicate', createdAt: '2024-01-01T00:00:00Z' },
      ];
      useChatStore.setState({ messages: [] });

      useChatStore.getState().reconcileMessages(serverMsgs);

      const result = useChatStore.getState().messages;
      expect(result).toHaveLength(1);
    });
  });
});
