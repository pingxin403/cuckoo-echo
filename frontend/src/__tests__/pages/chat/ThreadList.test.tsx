import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { useSessionStore } from '@/stores/sessionStore';
import ThreadList from '@/pages/chat/ThreadList';

beforeEach(() => {
  useSessionStore.setState({
    threads: [],
    activeThreadId: null,
    status: 'active',
    protocol: 'sse',
  });
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
});
