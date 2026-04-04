import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { useHitlStore } from '@/stores/adminStore';

// Mock useWebSocket hook
vi.mock('@/hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    send: vi.fn(),
    disconnect: vi.fn(),
    connectionStatus: 'connected' as const,
  }),
}));

// Mock apiClient
vi.mock('@/network/axios', () => ({
  default: {
    get: vi.fn().mockResolvedValue({ data: [] }),
    post: vi.fn().mockResolvedValue({ data: {} }),
  },
}));

// Mock showToast standalone function
vi.mock('@/components/Toast', async () => {
  const actual = await vi.importActual<typeof import('@/components/Toast')>('@/components/Toast');
  return {
    ...actual,
    showToast: vi.fn(),
  };
});

import HITLPanel from '@/pages/admin/HITLPanel';

beforeEach(() => {
  useHitlStore.setState({
    hitlSessions: [],
    activeHitlSession: null,
  });
});

function renderHITL() {
  return render(<HITLPanel />);
}

describe('HITLPanel', () => {
  it('renders session list area', async () => {
    renderHITL();
    // Wait for loading to finish — the component starts with isLoading=true
    // and sets it to false after the API call resolves
    expect(await screen.findByText('介入会话')).toBeInTheDocument();
  });

  it('renders placeholder when no active session', async () => {
    renderHITL();
    expect(await screen.findByText('选择一个会话开始处理')).toBeInTheDocument();
  });
});
