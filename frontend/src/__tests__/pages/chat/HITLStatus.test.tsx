import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { useSessionStore } from '@/stores/sessionStore';
import HITLStatus from '@/pages/chat/HITLStatus';

beforeEach(() => {
  vi.clearAllMocks();
  useSessionStore.setState({
    status: 'active',
    threads: [],
    activeThreadId: null,
    protocol: 'sse',
  });
});

describe('HITLStatus', () => {
  it('shows "已转接人工客服，请稍候" when status is hitl_active', () => {
    useSessionStore.setState({ status: 'hitl_active' });

    render(<HITLStatus />);

    expect(screen.getByText('已转接人工客服，请稍候')).toBeInTheDocument();
  });

  it('shows "已恢复 AI 客服" when status changes from hitl_active to active', () => {
    // Start with hitl_active
    useSessionStore.setState({ status: 'hitl_active' });
    const { rerender } = render(<HITLStatus />);
    expect(screen.getByText('已转接人工客服，请稍候')).toBeInTheDocument();

    // Transition to active
    act(() => {
      useSessionStore.setState({ status: 'active' });
    });
    rerender(<HITLStatus />);

    expect(screen.getByText('已恢复 AI 客服')).toBeInTheDocument();
  });

  it('shows nothing when status is active (no previous HITL)', () => {
    useSessionStore.setState({ status: 'active' });

    const { container } = render(<HITLStatus />);

    // Component returns null — no banner rendered
    expect(container.innerHTML).toBe('');
  });
});
