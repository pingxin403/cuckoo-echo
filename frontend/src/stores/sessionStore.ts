import { create } from 'zustand';
import { v4 as uuidv4 } from 'uuid';
import type { SessionStatus, ThreadMeta } from '@/types';

interface SessionState {
  status: SessionStatus;
  threads: ThreadMeta[];
  activeThreadId: string | null;
  protocol: 'sse' | 'websocket';

  createThread: () => string;
  switchThread: (threadId: string) => void;
  setStatus: (status: SessionStatus) => void;
  switchProtocol: (protocol: 'sse' | 'websocket') => void;
  addThread: (thread: ThreadMeta) => void;
  updateThread: (threadId: string, updates: Partial<ThreadMeta>) => void;
}

export const useSessionStore = create<SessionState>((set, get) => ({
  status: 'active',
  threads: [],
  activeThreadId: null,
  protocol: 'sse',

  createThread() {
    const id = uuidv4();
    const newThread: ThreadMeta = {
      id,
      title: '',
      lastMessageAt: new Date().toISOString(),
      messageCount: 0,
    };
    const threads = [newThread, ...get().threads];
    set({ threads, activeThreadId: id });
    return id;
  },

  switchThread(threadId: string) {
    set({ activeThreadId: threadId });
  },

  setStatus(status: SessionStatus) {
    set({ status });
  },

  switchProtocol(protocol: 'sse' | 'websocket') {
    set({ protocol });
  },

  addThread(thread: ThreadMeta) {
    const threads = [...get().threads, thread].sort(
      (a, b) =>
        new Date(b.lastMessageAt).getTime() -
        new Date(a.lastMessageAt).getTime(),
    );
    set({ threads });
  },

  updateThread(threadId: string, updates: Partial<ThreadMeta>) {
    set((state) => ({
      threads: state.threads.map((t) =>
        t.id === threadId ? { ...t, ...updates } : t,
      ),
    }));
  },
}));
