import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { useToast } from '@/components/Toast';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [emailError, setEmailError] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [loading, setLoading] = useState(false);

  const login = useAuthStore((s) => s.login);
  const navigate = useNavigate();
  const { showToast } = useToast();

  function validate(): boolean {
    let valid = true;

    if (!email.trim()) {
      setEmailError('请输入邮箱');
      valid = false;
    } else if (!EMAIL_RE.test(email.trim())) {
      setEmailError('邮箱格式不正确');
      valid = false;
    } else {
      setEmailError('');
    }

    if (!password) {
      setPasswordError('请输入密码');
      valid = false;
    } else {
      setPasswordError('');
    }

    return valid;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!validate() || loading) return;

    setLoading(true);
    try {
      await login(email.trim(), password);
      navigate('/admin/metrics', { replace: true });
    } catch {
      showToast('error', '邮箱或密码错误');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm rounded-xl bg-white p-8 shadow-lg">
        <h1 className="mb-6 text-center text-2xl font-semibold text-gray-900">
          登录 Cuckoo-Echo
        </h1>

        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          {/* Email */}
          <div>
            <label htmlFor="login-email" className="mb-1 block text-sm font-medium text-gray-700">
              邮箱
            </label>
            <input
              id="login-email"
              type="email"
              aria-label="邮箱"
              aria-invalid={!!emailError}
              aria-describedby={emailError ? 'login-email-error' : undefined}
              value={email}
              onChange={(e) => { setEmail(e.target.value); setEmailError(''); }}
              className={`w-full rounded-lg border px-3 py-2 text-sm outline-none transition focus:ring-2 focus:ring-blue-500 ${
                emailError ? 'border-red-400' : 'border-gray-300'
              }`}
              placeholder="admin@example.com"
              autoComplete="email"
              disabled={loading}
            />
            {emailError && (
              <p id="login-email-error" className="mt-1 text-xs text-red-500" role="alert">
                {emailError}
              </p>
            )}
          </div>

          {/* Password */}
          <div>
            <label htmlFor="login-password" className="mb-1 block text-sm font-medium text-gray-700">
              密码
            </label>
            <input
              id="login-password"
              type="password"
              aria-label="密码"
              aria-invalid={!!passwordError}
              aria-describedby={passwordError ? 'login-password-error' : undefined}
              value={password}
              onChange={(e) => { setPassword(e.target.value); setPasswordError(''); }}
              className={`w-full rounded-lg border px-3 py-2 text-sm outline-none transition focus:ring-2 focus:ring-blue-500 ${
                passwordError ? 'border-red-400' : 'border-gray-300'
              }`}
              placeholder="请输入密码"
              autoComplete="current-password"
              disabled={loading}
            />
            {passwordError && (
              <p id="login-password-error" className="mt-1 text-xs text-red-500" role="alert">
                {passwordError}
              </p>
            )}
          </div>

          {/* Submit */}
          <button
            type="submit"
            aria-label="登录"
            disabled={loading}
            className="w-full rounded-lg bg-blue-600 py-2 text-sm font-medium text-white transition hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? '登录中…' : '登录'}
          </button>
        </form>
      </div>
    </div>
  );
}
