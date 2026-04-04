import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { ToastProvider } from '@/components/Toast';
import { useSandboxStore } from '@/stores/adminStore';

// Mock apiClient
vi.mock('@/network/axios', () => ({
  default: {
    post: vi.fn().mockResolvedValue({ data: [] }),
  },
}));

import SandboxRunner from '@/pages/admin/SandboxRunner';

beforeEach(() => {
  useSandboxStore.setState({
    sandboxResults: [],
    isRunning: false,
  });
});

function renderSandbox() {
  return render(
    <BrowserRouter>
      <ToastProvider>
        <SandboxRunner />
      </ToastProvider>
    </BrowserRouter>,
  );
}

describe('SandboxRunner', () => {
  it('renders "沙盒测试" heading', () => {
    renderSandbox();
    expect(screen.getByText('沙盒测试')).toBeInTheDocument();
  });

  it('renders test case input form', () => {
    renderSandbox();
    expect(screen.getByText('测试用例')).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: '用例 1 查询' })).toBeInTheDocument();
  });

  it('renders "运行测试" button', () => {
    renderSandbox();
    expect(screen.getByRole('button', { name: '运行测试' })).toBeInTheDocument();
  });
});
