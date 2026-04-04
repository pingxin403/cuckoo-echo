import { create } from 'zustand';
import { v4 as uuidv4 } from 'uuid';
import type { Message, ConnectionStatus, MediaAttachment } from '@/types';
import apiClient from '@/network/axios';
import { saveThread, loadThread as loadCachedThread } from '@/lib/cache';

interface ChatState {
  messages: Message[];
  activeThreadId: string | null;
  isStreaming: boolean;
  streamingContent: string;
  connectionStatus: ConnectionStatus;
  error: string | null;

  sendMessage: (content: string, media?: MediaAttachment[]) => void;
  appendToken: (token: string) => void;
  finishStreaming: (messageId: string) => void;
  replaceTempId: (tempId: string, realId: string) => void;
  loadThread: (threadId: string) => Promise<void>;
  reconcileMessages: (serverMessages: Message[]) => void;
  setConnectionStatus: (status: ConnectionStatus) => void;
  setError: (error: string | null) => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  activeThreadId: null,
  isStreaming: false,
  streamingContent: '',
  connectionStatus: 'disconnected',
  error: null,

  sendMessage(content: string, media?: MediaAttachment[]) {
    const { activeThreadId, messages } = get();
    const tempId = `temp_${uuidv4()}`;
    const optimisticMessage: Message = {
      id: tempId,
      threadId: activeThreadId ?? '',
      role: 'user',
      content,
      mediaAttachments: media,
      createdAt: new Date().toISOString(),
      isOptimistic: true,
    };
    set({ messages: [...messages, optimisticMessage], isStreaming: true });
  },

  appendToken(token: string) {
    set((state) => ({ streamingContent: state.streamingContent + token }));
  },

  finishStreaming(messageId: string) {
    const { streamingContent, messages } = get();
    const updatedMessages = messages.map((msg) =>
      msg.id === messageId
        ? { ...msg, content: streamingContent || msg.content }
        : msg,
    );
    set({
      messages: updatedMessages,
      isStreaming: false,
      streamingContent: '',
    });
  },

  replaceTempId(tempId: string, realId: string) {
    set((state) => ({
      messages: state.messages.map((msg) =>
        msg.id === tempId
          ? { ...msg, id: realId, isOptimistic: false }
          : msg,
      ),
    }));
  },

  async loadThread(threadId: string) {
    // Try loading from IndexedDB cache first
    const cached = await loadCachedThread(threadId);
    if (cached) {
      set({
        messages: cached.messages,
        activeThreadId: threadId,
      });
    }

    // Fetch from server and persist to cache
    const res = await apiClient.get<{ messages: Message[] }>(
      `/v1/threads/${threadId}`,
    );
    const serverMessages = res.data.messages ?? [];
    set({
      messages: serverMessages,
      activeThreadId: threadId,
    });

    // Persist to IndexedDB cache in the background
    saveThread(threadId, {
      id: threadId,
      title: serverMessages[0]?.content.slice(0, 50) ?? '',
      lastMessageAt: serverMessages[serverMessages.length - 1]?.createdAt ?? new Date().toISOString(),
      messageCount: serverMessages.length,
    }, serverMessages).catch(() => {
      // Cache write failure is non-critical; silently ignore
    });
  },

  reconcileMessages(serverMessages: Message[]) {
    const { messages: localMessages } = get();

    // Build a set of server message IDs for fast lookup
    const serverIds = new Set(serverMessages.map((m) => m.id));

    // Keep unconfirmed optimistic messages that the server hasn't acknowledged
    const unconfirmedOptimistic = localMessages.filter(
      (m) => m.isOptimistic && !serverIds.has(m.id),
    );

    // Merge: all server messages + unconfirmed optimistic
    const merged = [...serverMessages, ...unconfirmedOptimistic];

    // Sort by createdAt ascending
    merged.sort(
      (a, b) =>
        new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime(),
    );

    // Deduplicate by id (keep first occurrence)
    const seen = new Set<string>();
    const deduped = merged.filter((m) => {
      if (seen.has(m.id)) return false;
      seen.add(m.id);
      return true;
    });

    set({ messages: deduped });
  },

  setConnectionStatus(status: ConnectionStatus) {
    set({ connectionStatus: status });
  },

  setError(error: string | null) {
    set({ error });
  },
}));
