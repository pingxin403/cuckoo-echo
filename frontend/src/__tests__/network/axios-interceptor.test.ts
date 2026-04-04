import { describe, it, expect } from 'vitest';
import { transformResponse, toSnakeCaseWithExplicit } from '@/network/fieldMapper';

/**
 * Tests for the Axios interceptor field transformation logic.
 * We test the transform functions directly since they're the core of the interceptor.
 */
describe('Axios Interceptor transforms', () => {
  describe('Response: snake_case → camelCase', () => {
    it('converts basic snake_case response', () => {
      const backend = { total_conversations: 100, human_transfer_rate: 0.15 };
      const result = transformResponse(backend, '/admin/v1/metrics/overview') as Record<string, unknown>;
      expect(result.totalConversations).toBe(100);
      expect(result.humanEscalationRate).toBe(0.15);
    });

    it('handles login response with access_token', () => {
      const backend = { access_token: 'jwt.token.here', token_type: 'bearer' };
      const result = transformResponse(backend, '/admin/v1/auth/login') as Record<string, unknown>;
      expect(result.accessToken).toBe('jwt.token.here');
    });

    it('handles array responses', () => {
      const backend = [
        { doc_id: 'abc', file_name: 'test.pdf' },
        { doc_id: 'def', file_name: 'test2.pdf' },
      ];
      const result = transformResponse(backend, '/admin/v1/knowledge/docs/*') as Record<string, unknown>[];
      expect(result).toHaveLength(2);
      expect(result[0].id).toBe('abc'); // doc_id → id via explicit rule
    });

    it('passes through null/undefined', () => {
      expect(transformResponse(null, '/any')).toBeNull();
      expect(transformResponse(undefined, '/any')).toBeUndefined();
    });

    it('passes through primitives', () => {
      expect(transformResponse('hello', '/any')).toBe('hello');
      expect(transformResponse(42, '/any')).toBe(42);
    });
  });

  describe('Request: camelCase → snake_case', () => {
    it('converts basic camelCase request', () => {
      const frontend = { systemPrompt: 'Hello', personaName: 'Bot' };
      const result = toSnakeCaseWithExplicit(frontend, '/admin/v1/config/persona') as Record<string, unknown>;
      expect(result.system_prompt).toBe('Hello');
      expect(result.persona_name).toBe('Bot');
    });

    it('applies explicit model config mapping', () => {
      const frontend = { primaryModel: 'gpt-4o', temperature: 0.7 };
      const result = toSnakeCaseWithExplicit(frontend, '/admin/v1/config/model') as Record<string, unknown>;
      expect(result.model).toBe('gpt-4o'); // primaryModel → model via explicit rule
    });

    it('skips FormData', () => {
      const formData = new FormData();
      expect(toSnakeCaseWithExplicit(formData, '/any')).toBe(formData);
    });

    it('handles nested objects', () => {
      const frontend = { rateLimitConfig: { tenantRps: 100, userRps: 10 } };
      const result = toSnakeCaseWithExplicit(frontend, '/admin/v1/config/rate-limit') as Record<string, unknown>;
      const nested = result.rate_limit_config as Record<string, unknown>;
      expect(nested.tenant_rps).toBe(100);
    });
  });

  describe('Structure adapters', () => {
    it('overview adapter adds computed fields', () => {
      const backend = { total_conversations: 50, human_transfer_rate: 0.2 };
      const result = transformResponse(backend, '/admin/v1/metrics/overview') as Record<string, unknown>;
      expect(result.aiResolutionRate).toBe(0.8); // 1 - 0.2
    });

    it('missed-queries adapter renames queryPrefix → query in array items', () => {
      const backend = { missed_queries: [{ query_prefix: 'how to', count: 5 }] };
      const result = transformResponse(backend, '/admin/v1/metrics/missed-queries') as Record<string, unknown>[];
      expect(Array.isArray(result)).toBe(true);
      expect((result as Record<string, unknown>[])[0].query).toBe('how to');
    });
  });
});
