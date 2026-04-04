import { describe, it, expect, beforeEach } from 'vitest';
import { useAuthStore } from '@/stores/authStore';

/**
 * Helper: build a minimal mock JWT with a known payload.
 * Format: header.payload.signature (only payload matters for our tests).
 */
function makeMockJwt(overrides: Partial<{
  sub: string;
  email: string;
  tenant_id: string;
  tenant_name: string;
  role: string;
  exp: number;
}> = {}): string {
  const payload = {
    sub: 'usr_001',
    email: 'admin@example.com',
    tenant_id: 'tenant_001',
    tenant_name: 'Demo Tenant',
    role: 'admin',
    exp: Math.floor(Date.now() / 1000) + 7200, // 2 hours from now
    ...overrides,
  };
  const encoded = btoa(JSON.stringify(payload));
  return `eyJhbGciOiJIUzI1NiJ9.${encoded}.mock_signature`;
}

// Reset store state before each test
beforeEach(() => {
  useAuthStore.setState({
    accessToken: null,
    user: null,
    isAuthenticated: false,
  });
});

describe('authStore', () => {
  describe('initial state', () => {
    it('starts as not authenticated with no token or user', () => {
      const state = useAuthStore.getState();
      expect(state.accessToken).toBeNull();
      expect(state.user).toBeNull();
      expect(state.isAuthenticated).toBe(false);
    });
  });

  describe('setAccessToken', () => {
    it('updates token, parses user from JWT payload, and sets isAuthenticated', () => {
      const token = makeMockJwt({
        sub: 'usr_42',
        email: 'test@corp.com',
        tenant_id: 'tn_99',
        tenant_name: 'Test Corp',
        role: 'editor',
      });

      useAuthStore.getState().setAccessToken(token);

      const state = useAuthStore.getState();
      expect(state.accessToken).toBe(token);
      expect(state.isAuthenticated).toBe(true);
      expect(state.user).toEqual({
        id: 'usr_42',
        email: 'test@corp.com',
        tenantId: 'tn_99',
        tenantName: 'Test Corp',
        role: 'editor',
      });
    });

    it('handles a second setAccessToken call (token rotation)', () => {
      const token1 = makeMockJwt({ sub: 'usr_1', email: 'a@a.com' });
      const token2 = makeMockJwt({ sub: 'usr_2', email: 'b@b.com' });

      useAuthStore.getState().setAccessToken(token1);
      expect(useAuthStore.getState().user?.id).toBe('usr_1');

      useAuthStore.getState().setAccessToken(token2);
      expect(useAuthStore.getState().user?.id).toBe('usr_2');
      expect(useAuthStore.getState().accessToken).toBe(token2);
    });
  });

  describe('checkTokenExpiry', () => {
    it('returns true when there is no token', () => {
      expect(useAuthStore.getState().checkTokenExpiry()).toBe(true);
    });

    it('returns true when token is already expired', () => {
      const expiredToken = makeMockJwt({
        exp: Math.floor(Date.now() / 1000) - 3600, // 1 hour ago
      });
      useAuthStore.getState().setAccessToken(expiredToken);

      expect(useAuthStore.getState().checkTokenExpiry()).toBe(true);
    });

    it('returns true when token expires within 1 hour (near expiry)', () => {
      const nearExpiryToken = makeMockJwt({
        exp: Math.floor(Date.now() / 1000) + 1800, // 30 minutes from now
      });
      useAuthStore.getState().setAccessToken(nearExpiryToken);

      expect(useAuthStore.getState().checkTokenExpiry()).toBe(true);
    });

    it('returns false when token has more than 1 hour remaining', () => {
      const freshToken = makeMockJwt({
        exp: Math.floor(Date.now() / 1000) + 7200, // 2 hours from now
      });
      useAuthStore.getState().setAccessToken(freshToken);

      expect(useAuthStore.getState().checkTokenExpiry()).toBe(false);
    });
  });
});
