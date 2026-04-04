import { create } from 'zustand';
import type { AdminUser } from '@/types';
import apiClient, {
  setTokenGetter,
  setTokenRefresher,
} from '@/network/axios';
import {
  refreshTokenWithMutex,
  setAuthCallbacks,
} from '@/lib/tokenRefresh';

interface AuthState {
  accessToken: string | null;
  user: AdminUser | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  setAccessToken: (token: string) => void;
  checkTokenExpiry: () => boolean;
}

/**
 * Decode the payload section of a JWT (base64url → JSON).
 * Returns the parsed payload object, or null on failure.
 */
/**
 * Decode the payload section of a JWT (base64url → JSON).
 * Supports both backend real format and mock format.
 */
interface JWTPayload {
  // Backend real format
  admin_user_id?: string;
  tenant_id: string;
  role: string;
  exp: number;
  iat?: number;
  // Mock/legacy format (may also be present)
  sub?: string;
  email?: string;
  tenant_name?: string;
}

function decodeJwtPayload(token: string): JWTPayload | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const base64 = parts[1]
      .replace(/-/g, '+')
      .replace(/_/g, '/');
    const json = atob(base64);
    return JSON.parse(json) as JWTPayload;
  } catch {
    return null;
  }
}

function userFromPayload(payload: JWTPayload): AdminUser {
  // Handle both backend real format (admin_user_id) and mock format (sub)
  const id = payload.admin_user_id ?? payload.sub ?? '';
  return {
    id,
    email: payload.email ?? id,                    // Fallback: use id as display name
    tenantId: payload.tenant_id,
    tenantName: payload.tenant_name ?? payload.tenant_id,  // Fallback: use tenant_id
    role: payload.role,
  };
}

export const useAuthStore = create<AuthState>((set, get) => ({
  accessToken: null,
  user: null,
  isAuthenticated: false,

  async login(email: string, password: string) {
    const res = await apiClient.post<{ access_token: string }>(
      '/admin/v1/auth/login',
      { email, password },
    );
    const token = res.data.access_token;
    const payload = decodeJwtPayload(token);
    set({
      accessToken: token,
      user: payload ? userFromPayload(payload) : null,
      isAuthenticated: true,
    });
  },

  logout() {
    set({ accessToken: null, user: null, isAuthenticated: false });
    // Fire-and-forget: tell backend to clear the refresh cookie
    apiClient.post('/admin/v1/auth/logout').catch(() => {});
    window.location.href = '/login';
  },

  setAccessToken(token: string) {
    const payload = decodeJwtPayload(token);
    set({
      accessToken: token,
      user: payload ? userFromPayload(payload) : null,
      isAuthenticated: true,
    });
  },

  checkTokenExpiry(): boolean {
    const { accessToken } = get();
    if (!accessToken) return true;
    const payload = decodeJwtPayload(accessToken);
    if (!payload) return true;
    const remainingMs = payload.exp * 1000 - Date.now();
    const ONE_HOUR_MS = 60 * 60 * 1000;
    return remainingMs < ONE_HOUR_MS;
  },
}));

// ─── Wire up callback integrations at module level ─────────────
setTokenGetter(() => useAuthStore.getState().accessToken);
setTokenRefresher(refreshTokenWithMutex);
setAuthCallbacks(
  (token: string) => useAuthStore.getState().setAccessToken(token),
  () => useAuthStore.getState().logout(),
);
