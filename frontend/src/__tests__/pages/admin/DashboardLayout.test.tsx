import { describe, it, expect, afterEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import DashboardLayout from '@/pages/admin/DashboardLayout';
import { useAuthStore } from '@/stores/authStore';

afterEach(() => {
  useAuthStore.setState({
    accessToken: null,
    user: null,
    isAuthenticated: false,
  });
});

function renderLayout() {
  useAuthStore.setState({
    isAuthenticated: true,
    user: {
      id: 'usr_001',
      email: 'admin@example.com',
      tenantId: 'tenant_001',
      tenantName: 'Demo Tenant',
      role: 'admin',
    },
  });

  return render(
    <MemoryRouter initialEntries={['/admin/metrics']}>
      <DashboardLayout />
    </MemoryRouter>,
  );
}

describe('DashboardLayout', () => {
  it('renders all 5 navigation links', () => {
    renderLayout();
    expect(screen.getByText('数据看板')).toBeInTheDocument();
    expect(screen.getByText('知识库管理')).toBeInTheDocument();
    expect(screen.getByText('人工介入')).toBeInTheDocument();
    expect(screen.getByText('配置中心')).toBeInTheDocument();
    expect(screen.getByText('沙盒测试')).toBeInTheDocument();
  });

  it('shows user email from authStore', () => {
    renderLayout();
    expect(screen.getByText('admin@example.com')).toBeInTheDocument();
  });

  it('logout button calls authStore.logout', () => {
    const logoutSpy = vi.fn();
    useAuthStore.setState({ logout: logoutSpy });

    renderLayout();
    fireEvent.click(screen.getByText('退出登录'));
    expect(logoutSpy).toHaveBeenCalled();
  });
});
