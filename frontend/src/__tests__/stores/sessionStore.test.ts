import { describe, it, expect, beforeEach } from 'vitest';
import { useSessionStore } from '@/stores/sessionStore';

// Reset store state before each test
beforeEach(() => {
  useSessionStore.setState({
    status: 'active',
    threads: [],
    activeThreadId: null,
    protocol: 'sse',
  });
});

describe('sessionStore', () => {
  describe('createThread', () => {
    it('generates a uuid, adds to threads, and sets activeThreadId', () => {
      const id = useSessionStore.getState().createThread();

      const state = useSessionStore.getState();
      expect(id).toBeTruthy();
      // UUID v4 format
      expect(id).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i);
      expect(state.activeThreadId).toBe(id);
      expect(state.threads).toHaveLength(1);
      expect(state.threads[0].id).toBe(id);
      expect(state.threads[0].title).toBe('');
      expect(state.threads[0].messageCount).toBe(0);
    });

    it('prepends new thread to the list', () => {
      const id1 = useSessionStore.getState().createThread();
      const id2 = useSessionStore.getState().createThread();

      const state = useSessionStore.getState();
      expect(state.threads).toHaveLength(2);
      // Newest first
      expect(state.threads[0].id).toBe(id2);
      expect(state.threads[1].id).toBe(id1);
      expect(state.activeThreadId).toBe(id2);
    });
  });

  describe('switchThread', () => {
    it('updates activeThreadId', () => {
      useSessionStore.getState().createThread();
      const id2 = useSessionStore.getState().createThread();
      const id1 = useSessionStore.getState().threads[1].id;

      // Currently active is id2
      expect(useSessionStore.getState().activeThreadId).toBe(id2);

      useSessionStore.getState().switchThread(id1);
      expect(useSessionStore.getState().activeThreadId).toBe(id1);
    });
  });

  describe('setStatus', () => {
    it('transitions active → hitl_pending', () => {
      expect(useSessionStore.getState().status).toBe('active');

      useSessionStore.getState().setStatus('hitl_pending');
      expect(useSessionStore.getState().status).toBe('hitl_pending');
    });

    it('transitions hitl_pending → hitl_active', () => {
      useSessionStore.getState().setStatus('hitl_pending');

      useSessionStore.getState().setStatus('hitl_active');
      expect(useSessionStore.getState().status).toBe('hitl_active');
    });

    it('transitions hitl_active → resolved', () => {
      useSessionStore.getState().setStatus('hitl_active');

      useSessionStore.getState().setStatus('resolved');
      expect(useSessionStore.getState().status).toBe('resolved');
    });

    it('can transition back to active from resolved', () => {
      useSessionStore.getState().setStatus('resolved');

      useSessionStore.getState().setStatus('active');
      expect(useSessionStore.getState().status).toBe('active');
    });
  });

  describe('switchProtocol', () => {
    it('updates protocol from sse to websocket', () => {
      expect(useSessionStore.getState().protocol).toBe('sse');

      useSessionStore.getState().switchProtocol('websocket');
      expect(useSessionStore.getState().protocol).toBe('websocket');
    });

    it('updates protocol from websocket to sse', () => {
      useSessionStore.getState().switchProtocol('websocket');

      useSessionStore.getState().switchProtocol('sse');
      expect(useSessionStore.getState().protocol).toBe('sse');
    });
  });
});
