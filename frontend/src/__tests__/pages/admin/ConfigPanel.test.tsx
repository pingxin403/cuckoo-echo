import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { ToastProvider } from '@/components/Toast';
import { useConfigStore } from '@/stores/adminStore';

// Mock apiClient
vi.mock('@/network/axios', () => ({
  default: {
    get: vi.fn().mockResolvedValue({
      data: {
        persona: { systemPrompt: '', personaName: '', greeting: '' },
        model: { primaryModel: 'gpt-4o', fallbackModel: 'gpt-4o-mini', temperature: 0.7 },
        rateLimit: { tenantRps: 100, userRps: 10 },
      },
    }),
    put: vi.fn().mockResolvedValue({ data: {} }),
    post: vi.fn().mockResolvedValue({ data: {} }),
  },
}));

import ConfigPanel from '@/pages/admin/ConfigPanel';

beforeEach(() => {
  useConfigStore.setState({
    persona: null,
    modelConfig: null,
    rateLimitConfig: null,
  });
});

function renderConfig() {
  return render(
    <BrowserRouter>
      <ToastProvider>
        <ConfigPanel />
      </ToastProvider>
    </BrowserRouter>,
  );
}

describe('ConfigPanel', () => {
  it('renders "配置中心" heading', () => {
    renderConfig();
    expect(screen.getByText('配置中心')).toBeInTheDocument();
  });

  it('renders persona, model, and rate-limit sections', () => {
    renderConfig();
    expect(screen.getByRole('region', { name: 'Persona 配置' })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: '模型配置' })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: '限流配置' })).toBeInTheDocument();
  });

  it('renders embed code generator section', () => {
    renderConfig();
    expect(screen.getByRole('region', { name: '嵌入代码生成器' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '复制嵌入代码' })).toBeInTheDocument();
  });
});
