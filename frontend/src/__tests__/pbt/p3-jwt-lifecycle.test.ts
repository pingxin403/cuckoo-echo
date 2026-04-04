// Feature: frontend-ui, Property 3: JWT 令牌生命周期不变量
// **Validates: Requirements 4.2, 4.4, 4.6**

import { describe, it, expect, beforeEach } from 'vitest';
import fc from 'fast-check';
import { useAuthStore } from '@/stores/authStore';

/**
 * Helper: build a mock JWT with a given exp timestamp (in seconds).
 */
function makeMockJwt(expSeconds: number): string {
  const payload = {
    sub: 'usr_001',
    email: 'admin@example.com',
    tenant_id: 'tenant_001',
    tenant_name: 'Demo Tenant',
    role: 'admin',
    exp: expSeconds,
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

const ONE_HOUR_S = 3600;

describe('Property 3: JWT 令牌生命周期不变量', () => {
  it('checkTokenExpiry returns true for expired tokens (exp in the past)', () => {
    fc.assert(
      fc.property(
        // Random past expiry: 1 second to 30 days ago
        fc.integer({ min: 1, max: 30 * 24 * 3600 }),
        (secondsAgo) => {
          const expSeconds = Math.floor(Date.now() / 1000) - secondsAgo;
          const token = makeMockJwt(expSeconds);
          useAuthStore.getState().setAccessToken(token);

          // Expired token → checkTokenExpiry should return true
          expect(useAuthStore.getState().checkTokenExpiry()).toBe(true);
        },
      ),
      { numRuns: 150 },
    );
  });

  it('checkTokenExpiry returns true for near-expiry tokens (remaining < 1 hour)', () => {
    fc.assert(
      fc.property(
        // Random near-expiry: 1 second to 59 minutes from now
        fc.integer({ min: 1, max: ONE_HOUR_S - 1 }),
        (secondsRemaining) => {
          const expSeconds = Math.floor(Date.now() / 1000) + secondsRemaining;
          const token = makeMockJwt(expSeconds);
          useAuthStore.getState().setAccessToken(token);

          // Near-expiry (< 1 hour remaining) → checkTokenExpiry should return true
          expect(useAuthStore.getState().checkTokenExpiry()).toBe(true);
        },
      ),
      { numRuns: 150 },
    );
  });

  it('checkTokenExpiry returns false for tokens with > 1 hour remaining', () => {
    fc.assert(
      fc.property(
        // Random future expiry: 1 hour + 1 second to 30 days from now
        fc.integer({ min: ONE_HOUR_S + 1, max: 30 * 24 * 3600 }),
        (secondsRemaining) => {
          const expSeconds = Math.floor(Date.now() / 1000) + secondsRemaining;
          const token = makeMockJwt(expSeconds);
          useAuthStore.getState().setAccessToken(token);

          // Plenty of time remaining → checkTokenExpiry should return false
          expect(useAuthStore.getState().checkTokenExpiry()).toBe(false);
        },
      ),
      { numRuns: 150 },
    );
  });

  it('no token means expired (checkTokenExpiry returns true)', () => {
    fc.assert(
      fc.property(
        fc.constant(null),
        () => {
          useAuthStore.setState({ accessToken: null });

          // No token → should be treated as expired
          expect(useAuthStore.getState().checkTokenExpiry()).toBe(true);
        },
      ),
      { numRuns: 100 },
    );
  });

  it('expired token + no valid refresh means no valid token state', () => {
    fc.assert(
      fc.property(
        // Random past expiry
        fc.integer({ min: 1, max: 30 * 24 * 3600 }),
        (secondsAgo) => {
          const expSeconds = Math.floor(Date.now() / 1000) - secondsAgo;
          const token = makeMockJwt(expSeconds);
          useAuthStore.getState().setAccessToken(token);

          // Token is expired
          const isExpired = useAuthStore.getState().checkTokenExpiry();
          expect(isExpired).toBe(true);

          // Simulate refresh failure by calling logout
          useAuthStore.setState({
            accessToken: null,
            user: null,
            isAuthenticated: false,
          });

          // After logout, no valid token exists
          expect(useAuthStore.getState().accessToken).toBeNull();
          expect(useAuthStore.getState().isAuthenticated).toBe(false);
          expect(useAuthStore.getState().checkTokenExpiry()).toBe(true);
        },
      ),
      { numRuns: 150 },
    );
  });
});
