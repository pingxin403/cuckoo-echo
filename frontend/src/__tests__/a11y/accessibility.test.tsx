import { describe, it, expect, beforeAll, afterAll, afterEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ToastProvider, useToast } from '@/components/Toast';
import LoginPage from '@/pages/LoginPage';
import DashboardLayout from '@/pages/admin/DashboardLayout';
import { ConfirmDialog } from '@/components/ConfirmDialog';
import { OfflineBanner } from '@/components/OfflineBanner';
import { Skeleton } from '@/components/Skeleton';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { useAuthStore } from '@/stores/authStore';
import { server } from '@/mocks/server';

beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }));
afterEach(() => {
  server.resetHandlers();
  useAuthStore.setState({ accessToken: null, user: null, isAuthenticated: false });
});
afterAll(() => server.close());

// ---------------------------------------------------------------------------
// 1. LoginPage aria-labels
// ---------------------------------------------------------------------------
describe('LoginPage accessibility', () => {
  function renderLogin() {
    return render(
      <MemoryRouter>
        <ToastProvider>
          <LoginPage />
        </ToastProvider>
      </MemoryRouter>,
    );
  }

  it('email input has aria-label="邮箱"', () => {
    renderLogin();
    const email = screen.getByLabelText('邮箱');
    expect(email).toBeInTheDocument();
    expect(email.tagName).toBe('INPUT');
  });

  it('password input has aria-label="密码"', () => {
    renderLogin();
    const pw = screen.getByLabelText('密码');
    expect(pw).toBeInTheDocument();
    expect(pw.tagName).toBe('INPUT');
  });

  it('submit button has aria-label="登录"', () => {
    renderLogin();
    const btn = screen.getByRole('button', { name: '登录' });
    expect(btn).toBeInTheDocument();
  });
});


// ---------------------------------------------------------------------------
// 2. DashboardLayout navigation
// ---------------------------------------------------------------------------
describe('DashboardLayout accessibility', () => {
  function renderDashboard() {
    useAuthStore.setState({
      accessToken: 'fake',
      user: { id: '1', email: 'a@b.com', tenantId: 't1', tenantName: 'T', role: 'admin' },
      isAuthenticated: true,
    });
    return render(
      <MemoryRouter initialEntries={['/admin/metrics']}>
        <DashboardLayout />
      </MemoryRouter>,
    );
  }

  it('nav has aria-label="管理后台导航"', () => {
    renderDashboard();
    const nav = screen.getByRole('navigation', { name: '管理后台导航' });
    expect(nav).toBeInTheDocument();
  });

  it('all nav links are keyboard-focusable (<a> elements)', () => {
    renderDashboard();
    const nav = screen.getByRole('navigation', { name: '管理后台导航' });
    const links = nav.querySelectorAll('a');
    expect(links.length).toBeGreaterThan(0);
    links.forEach((link) => {
      expect(link.tagName).toBe('A');
    });
  });
});

// ---------------------------------------------------------------------------
// 3. ConfirmDialog aria attributes
// ---------------------------------------------------------------------------
describe('ConfirmDialog accessibility', () => {
  it('has aria-label="确认对话框" and buttons with aria-labels', () => {
    render(
      <ConfirmDialog
        open={true}
        onOpenChange={() => {}}
        title="删除确认"
        description="确定要删除吗？"
        onConfirm={() => {}}
        confirmLabel="确认"
        cancelLabel="取消"
      />,
    );

    // Radix AlertDialog uses aria-labelledby (title) for accessible name computation,
    // but our custom aria-label="确认对话框" is still present on the element
    const dialog = screen.getByRole('alertdialog');
    expect(dialog).toBeInTheDocument();
    expect(dialog).toHaveAttribute('aria-label', '确认对话框');

    const cancelBtn = screen.getByRole('button', { name: '取消' });
    expect(cancelBtn).toBeInTheDocument();

    const confirmBtn = screen.getByRole('button', { name: '确认' });
    expect(confirmBtn).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// 4. Toast notifications aria-labels
// ---------------------------------------------------------------------------
function ToastTrigger() {
  const { showToast } = useToast();
  return (
    <>
      <button onClick={() => showToast('success', 'ok')}>trigger-success</button>
      <button onClick={() => showToast('error', 'fail')}>trigger-error</button>
      <button onClick={() => showToast('info', 'note')}>trigger-info</button>
    </>
  );
}

describe('Toast accessibility', () => {
  it('success/error/info toasts have appropriate aria-labels', async () => {
    render(
      <ToastProvider>
        <ToastTrigger />
      </ToastProvider>,
    );

    fireEvent.click(screen.getByText('trigger-success'));
    fireEvent.click(screen.getByText('trigger-error'));
    fireEvent.click(screen.getByText('trigger-info'));

    expect(await screen.findByLabelText('成功提示')).toBeInTheDocument();
    expect(await screen.findByLabelText('错误提示')).toBeInTheDocument();
    expect(await screen.findByLabelText('信息提示')).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// 5. OfflineBanner aria-live
// ---------------------------------------------------------------------------
describe('OfflineBanner accessibility', () => {
  it('has aria-live="assertive" when offline', () => {
    Object.defineProperty(navigator, 'onLine', { value: false, writable: true, configurable: true });

    const { container } = render(<OfflineBanner />);
    const banner = container.querySelector('[aria-live="assertive"]');
    expect(banner).toBeInTheDocument();

    Object.defineProperty(navigator, 'onLine', { value: true, writable: true, configurable: true });
  });
});

// ---------------------------------------------------------------------------
// 6. Skeleton role and aria-label
// ---------------------------------------------------------------------------
describe('Skeleton accessibility', () => {
  it.each(['card', 'list', 'text'] as const)(
    '%s variant has role="status" and aria-label="Loading"',
    (variant) => {
      render(<Skeleton variant={variant} />);
      const el = screen.getByRole('status');
      expect(el).toHaveAttribute('aria-label', 'Loading');
    },
  );
});

// ---------------------------------------------------------------------------
// 7. ErrorBoundary fallback role
// ---------------------------------------------------------------------------
describe('ErrorBoundary accessibility', () => {
  it('fallback has role="alert"', () => {
    function Bomb(): React.ReactElement {
      throw new Error('boom');
    }

    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});

    render(
      <ErrorBoundary>
        <Bomb />
      </ErrorBoundary>,
    );

    const alert = screen.getByRole('alert');
    expect(alert).toBeInTheDocument();

    spy.mockRestore();
  });
});
