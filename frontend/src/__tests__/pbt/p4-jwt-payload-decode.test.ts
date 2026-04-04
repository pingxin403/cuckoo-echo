// Feature: frontend-integration, Property 4: JWT Payload 解码与回退字段
// **Validates: Requirements 3.2**

import { describe, it, expect } from 'vitest';
import fc from 'fast-check';
import type { AdminUser } from '@/types';

/**
 * Replicate the JWT decode logic from authStore for testing.
 * We test the pure decode + mapping logic without Zustand store dependency.
 */
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
    const json = atob(base64);
    return JSON.parse(json) as JWTPayload;
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

/**
 * Arbitrary: generates a non-empty alphanumeric string.
 */
const arbNonEmptyString = fc
  .array(
    fc.constantFrom(
      ...'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-'.split(
        '',
      ),
    ),
    { minLength: 1, maxLength: 30 },
  )
  .map((chars) => chars.join(''));

/**
 * Build a mock JWT from a payload object.
 * Format: header.payload.signature (base64url encoded).
 */
function buildMockJwt(payload: Record<string, unknown>): string {
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const body = btoa(JSON.stringify(payload));
  const signature = 'mock_signature';
  return `${header}.${body}.${signature}`;
}

describe('Property 4: JWT Payload 解码与回退字段', () => {
  it('decoded AdminUser has non-empty id, email, tenantId, tenantName, role', () => {
    fc.assert(
      fc.property(
        arbNonEmptyString,
        arbNonEmptyString,
        arbNonEmptyString,
        (adminUserId, tenantId, role) => {
          const payload = {
            admin_user_id: adminUserId,
            tenant_id: tenantId,
            role,
            exp: Math.floor(Date.now() / 1000) + 3600,
            iat: Math.floor(Date.now() / 1000),
          };

          const token = buildMockJwt(payload);
          const decoded = decodeJwtPayload(token);
          expect(decoded).not.toBeNull();

          const user = userFromPayload(decoded!);

          // All fields must be non-empty strings
          expect(user.id.length).toBeGreaterThan(0);
          expect(user.email.length).toBeGreaterThan(0);
          expect(user.tenantId.length).toBeGreaterThan(0);
          expect(user.tenantName.length).toBeGreaterThan(0);
          expect(user.role.length).toBeGreaterThan(0);

          // id should equal admin_user_id
          expect(user.id).toBe(adminUserId);
          // tenantId should equal tenant_id
          expect(user.tenantId).toBe(tenantId);
          // role should equal role
          expect(user.role).toBe(role);
          // email falls back to admin_user_id when not present
          expect(user.email).toBe(adminUserId);
          // tenantName falls back to tenant_id when not present
          expect(user.tenantName).toBe(tenantId);
        },
      ),
      { numRuns: 150 },
    );
  });
});
