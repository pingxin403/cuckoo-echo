import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { useKnowledgeStore } from '@/stores/adminStore';

// Mock apiClient to prevent real network calls
vi.mock('@/network/axios', () => ({
  default: {
    get: vi.fn().mockResolvedValue({ data: [] }),
    post: vi.fn().mockResolvedValue({ data: {} }),
    delete: vi.fn().mockResolvedValue({ data: {} }),
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

import KnowledgeManager from '@/pages/admin/KnowledgeManager';

beforeEach(() => {
  useKnowledgeStore.setState({
    documents: [],
    docFilter: { search: '', status: 'all' },
    isLoading: false,
  });
});

function renderKnowledge() {
  return render(<KnowledgeManager />);
}

describe('KnowledgeManager', () => {
  it('renders "知识库管理" heading', () => {
    renderKnowledge();
    expect(screen.getByText('知识库管理')).toBeInTheDocument();
  });

  it('renders upload zone', () => {
    renderKnowledge();
    expect(screen.getByRole('region', { name: '文档上传区域' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '选择文件上传' })).toBeInTheDocument();
  });

  it('renders search input and status filter buttons', () => {
    renderKnowledge();
    expect(screen.getByRole('textbox', { name: '搜索文件名' })).toBeInTheDocument();
    expect(screen.getByRole('group', { name: '状态筛选' })).toBeInTheDocument();
    expect(screen.getByText('全部')).toBeInTheDocument();
    expect(screen.getByText('已完成')).toBeInTheDocument();
    expect(screen.getByText('失败')).toBeInTheDocument();
  });
});
