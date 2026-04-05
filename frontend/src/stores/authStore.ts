import { create } from 'zustand';
import { persist } from 'zustand/middleware';
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

interface JWTPayload {
  admin_user_id?: string;
  tenant_id: string;
  role: string;
  exp: number;
  iat?: number;
  sub?: string;
  email?: string;
  tenant_name?: string;
}

function decodeJwtPayload(token: string): JWTPayload | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    return JSON.parse(atob(base64)) as JWTPayload;
  } catch {
    return null;
  }
}

function userFromPayload(payload: JWTPayload): AdminUser {
  const id = payload.admin_user_id ?? payload.sub ?? '';
  return {
    id,
    email: payload.email ?? id,
    tenantId: payload.tenant_id,
    tenantName: payload.tenant_name ?? payload.tenant_id,
    role: payload.role,
  };
}

/** Check if a token is expired or will expire within 60s */
function isTokenExpired(token: string): boolean {
  const payload = decodeJwtPayload(token);
  if (!payload) return true;
  return payload.exp * 1000 - Date.now() < 60_000;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      user: null,
      isAuthenticated: false,

      async login(email: string, password: string) {
        const res = await apiClient.post<{ accessToken: string; access_token?: string }>(
          '/admin/v1/auth/login',
          { email, password },
        );
        const token = res.data.accessToken ?? res.data.access_token ?? '';
        const payload = decodeJwtPayload(token);
        set({
          accessToken: token,
          user: payload ? userFromPayload(payload) : null,
          isAuthenticated: true,
        });
      },

      logout() {
        set({ accessToken: null, user: null, isAuthenticated: false });
        import('axios').then(({ default: rawAxios }) => {
          rawAxios.post('/admin/v1/auth/logout', null, { withCredentials: true }).catch(() => {});
        });
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
        return payload.exp * 1000 - Date.now() < 60 * 60 * 1000;
      },
    }),
    {
      name: 'cuckoo-auth',
      // Only persist token and user, not functions
      partialize: (state) => ({
        accessToken: state.accessToken,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
      // On rehydrate: validate token is not expired
      onRehydrateStorage: () => (state) => {
        if (state?.accessToken && isTokenExpired(state.accessToken)) {
          state.accessToken = null;
          state.user = null;
          state.isAuthenticated = false;
        }
      },
    },
  ),
);

// Wire up callback integrations
setTokenGetter(() => useAuthStore.getState().accessToken);
setTokenRefresher(refreshTokenWithMutex);
setAuthCallbacks(
  (token: string) => useAuthStore.getState().setAccessToken(token),
  () => useAuthStore.getState().logout(),
);
