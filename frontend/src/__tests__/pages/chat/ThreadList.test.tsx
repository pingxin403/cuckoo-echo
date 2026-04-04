import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { useSessionStore } from '@/stores/sessionStore';
import { useChatStore } from '@/stores/chatStore';
import ThreadList from '@/pages/chat/ThreadList';

// Spy on chatStore's loadThread
const loadThreadSpy = vi.fn();

beforeEach(() => {
  useSessionStore.setState({
    threads: [],
    activeThreadId: null,
    status: 'active',
    protocol: 'sse',
  });
  // Override loadThread with a spy
  useChatStore.setState({ loadThread: loadThreadSpy as unknown as (threadId: string) => Promise<void> });
  vi.clearAllMocks();
});

describe('ThreadList', () => {
  it('renders "新建会话" button', () => {
    render(<ThreadList />);
    expect(screen.getByRole('button', { name: '新建会话' })).toBeInTheDocument();
  });

  it('renders "暂无会话" when threads list is empty', () => {
    render(<ThreadList />);
    expect(screen.getByText('暂无会话')).toBeInTheDocument();
  });

  it('renders thread list from sessionStore', () => {
    useSessionStore.setState({
      threads: [
        { id: 't1', title: '第一个会话', lastMessageAt: new Date().toISOString(), messageCount: 5 },
        { id: 't2', title: '第二个会话', lastMessageAt: new Date().toISOString(), messageCount: 3 },
      ],
      activeThreadId: 't1',
    });

    render(<ThreadList />);

    expect(screen.getByText('第一个会话')).toBeInTheDocument();
    expect(screen.getByText('第二个会话')).toBeInTheDocument();
    expect(screen.getByText('5 条')).toBeInTheDocument();
    expect(screen.getByText('3 条')).toBeInTheDocument();
  });

  it('"新建会话" button calls createThread', () => {
    const createThreadSpy = vi.fn();
    useSessionStore.setState({ createThread: createThreadSpy as unknown as () => string });

    render(<ThreadList />);
    fireEvent.click(screen.getByRole('button', { name: '新建会话' }));

    expect(createThreadSpy).toHaveBeenCalledTimes(1);
  });

  it('clicking a thread calls switchThread + loadThread', () => {
    const switchThreadSpy = vi.fn();
    useSessionStore.setState({
      threads: [
        { id: 't1', title: '测试会话', lastMessageAt: new Date().toISOString(), messageCount: 2 },
      ],
      activeThreadId: null,
      switchThread: switchThreadSpy,
    });

    render(<ThreadList />);
    fireEvent.click(screen.getByLabelText('会话: 测试会话'));

    expect(switchThreadSpy).toHaveBeenCalledWith('t1');
    expect(loadThreadSpy).toHaveBeenCalledWith('t1');
  });
});
