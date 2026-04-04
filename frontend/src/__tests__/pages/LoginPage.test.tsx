import { describe, it, expect, beforeAll, afterAll, afterEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { ToastProvider } from '@/components/Toast';
import LoginPage from '@/pages/LoginPage';
import { useAuthStore } from '@/stores/authStore';
import { server } from '@/mocks/server';
import { http, HttpResponse } from 'msw';

beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }));
afterEach(() => {
  server.resetHandlers();
  useAuthStore.setState({
    accessToken: null,
    user: null,
    isAuthenticated: false,
  });
});
afterAll(() => server.close());

function renderLogin() {
  return render(
    <BrowserRouter>
      <ToastProvider>
        <LoginPage />
      </ToastProvider>
    </BrowserRouter>,
  );
}

describe('LoginPage', () => {
  it('renders email and password inputs', () => {
    renderLogin();
    expect(screen.getByLabelText('邮箱')).toBeInTheDocument();
    expect(screen.getByLabelText('密码')).toBeInTheDocument();
  });

  it('shows validation errors on empty submit', async () => {
    renderLogin();
    fireEvent.click(screen.getByRole('button', { name: '登录' }));
    await waitFor(() => {
      expect(screen.getByText('请输入邮箱')).toBeInTheDocument();
      expect(screen.getByText('请输入密码')).toBeInTheDocument();
    });
  });

  it('shows email format error for invalid email', async () => {
    renderLogin();
    fireEvent.change(screen.getByLabelText('邮箱'), { target: { value: 'not-an-email' } });
    fireEvent.change(screen.getByLabelText('密码'), { target: { value: 'password' } });
    fireEvent.click(screen.getByRole('button', { name: '登录' }));
    await waitFor(() => {
      expect(screen.getByText('邮箱格式不正确')).toBeInTheDocument();
    });
  });

  it('calls authStore.login on valid submit', async () => {
    const loginSpy = vi.fn(useAuthStore.getState().login);
    useAuthStore.setState({ login: loginSpy });
    renderLogin();
    fireEvent.change(screen.getByLabelText('邮箱'), { target: { value: 'admin@example.com' } });
    fireEvent.change(screen.getByLabelText('密码'), { target: { value: 'password' } });
    fireEvent.click(screen.getByRole('button', { name: '登录' }));
    await waitFor(() => {
      expect(loginSpy).toHaveBeenCalledWith('admin@example.com', 'password');
    });
  });

  it('shows error toast on login failure', async () => {
    server.use(
      http.post('*/admin/v1/auth/login', () => {
        return new HttpResponse(null, { status: 401 });
      }),
    );
    renderLogin();
    fireEvent.change(screen.getByLabelText('邮箱'), { target: { value: 'admin@example.com' } });
    fireEvent.change(screen.getByLabelText('密码'), { target: { value: 'wrong-password' } });
    fireEvent.click(screen.getByRole('button', { name: '登录' }));
    await waitFor(() => {
      expect(screen.getByText('邮箱或密码错误')).toBeInTheDocument();
    });
  });
});
