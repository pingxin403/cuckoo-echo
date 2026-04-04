import axios from 'axios';
import type { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { showToast } from '@/components/Toast';
import { analytics } from '@/lib/analytics';
import { transformResponse, toSnakeCaseWithExplicit } from '@/network/fieldMapper';

// ─── Token getter (callback pattern) ──────────────────────────
// AuthStore doesn't exist yet; consumers call setTokenGetter()
// once the store is ready.
let getAccessToken: () => string | null = () => null;

export function setTokenGetter(fn: () => string | null) {
  getAccessToken = fn;
}

// ─── Placeholder for token refresh (task 3.2) ─────────────────
let refreshTokenWithMutex: () => Promise<string | null> = () =>
  Promise.resolve(null);

export function setTokenRefresher(fn: () => Promise<string | null>) {
  refreshTokenWithMutex = fn;
}

// ─── Placeholder for error map (task 3.5) ──────────────────────
const FALLBACK_ERROR_MAP: Record<number, string> = {
  401: '登录已过期，请重新登录',
  404: '请求的资源不存在',
  409: 'AI 正在处理上一条消息，请稍候',
  413: '文件过大（最大 50MB）',
  415: '不支持该文件格式',
  429: '请求过于频繁，请稍后重试',
  500: '服务器内部错误，请稍后重试',
  503: '系统繁忙，请稍后重试',
};

let getErrorMap: () => Record<number, string> = () => FALLBACK_ERROR_MAP;

export function setErrorMap(fn: () => Record<number, string>) {
  getErrorMap = fn;
}

// ─── Axios instance ────────────────────────────────────────────
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL as string | undefined,
  timeout: 30_000,
  withCredentials: true,
});

// ─── Request Interceptor: inject Bearer token + camelCase → snake_case ──
apiClient.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  // Convert request body from camelCase to snake_case (skip FormData)
  if (config.data && typeof config.data === 'object' && !(config.data instanceof FormData)) {
    const endpoint = config.url ?? '';
    config.data = toSnakeCaseWithExplicit(config.data, endpoint);
  }
  return config;
});

// ─── Retry-after helper ────────────────────────────────────────
function parseRetryAfter(header: string | null | undefined): number {
  if (!header) return 1_000;
  const seconds = Number(header);
  if (!Number.isNaN(seconds) && seconds > 0) return seconds * 1_000;
  // RFC 7231: HTTP-date format
  const date = Date.parse(header);
  if (!Number.isNaN(date)) {
    const delta = date - Date.now();
    return delta > 0 ? delta : 1_000;
  }
  return 1_000;
}

// ─── Extend AxiosRequestConfig for retry flag ──────────────────
interface RetryableConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

// ─── Response Interceptor: snake_case → camelCase + error handling ──────
apiClient.interceptors.response.use(
  (response) => {
    // Convert response data from snake_case to camelCase + structure adapters
    const endpoint = response.config.url ?? '';
    if (response.data && typeof response.data === 'object') {
      response.data = transformResponse(response.data, endpoint);
    }
    return response;
  },
  async (error: AxiosError) => {
    const config = error.config as RetryableConfig | undefined;
    const status = error.response?.status;

    // Network Error (backend unavailable / ECONNREFUSED)
    if (!error.response && error.code === 'ERR_NETWORK') {
      showToast('error', '后端服务不可用，请检查服务状态');
      analytics.track('error_occurred', { status_code: 0, endpoint: error.config?.url, error_type: 'NETWORK_ERROR' });
      return Promise.reject(error);
    }

    // 401 → attempt token refresh then retry
    if (status === 401 && config && !config._retry) {
      config._retry = true;
      try {
        const newToken = await refreshTokenWithMutex();
        if (newToken) {
          config.headers.Authorization = `Bearer ${newToken}`;
          return apiClient(config);
        }
      } catch {
        // refresh failed – fall through to redirect
      }
      // Refresh failed or returned null → redirect to login
      window.location.href = '/login';
      return Promise.reject(error);
    }

    // 429 → read Retry-After, delay, then retry once
    if (status === 429 && config && !config._retry) {
      config._retry = true;
      const retryAfterMs = parseRetryAfter(
        error.response?.headers?.['retry-after'] as string | undefined,
      );
      await new Promise((r) => setTimeout(r, retryAfterMs));
      return apiClient(config);
    }

    // Map status code to user-friendly message and show toast
    if (status && status !== 401) {
      const errorMap = getErrorMap();
      const message = errorMap[status] ?? '未知错误，请稍后重试';
      showToast('error', message);
    }

    analytics.track('error_occurred', { status_code: status, endpoint: error.config?.url });

    return Promise.reject(error);
  },
);

export default apiClient;
