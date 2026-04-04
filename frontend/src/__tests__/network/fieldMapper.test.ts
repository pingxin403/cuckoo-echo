import { describe, it, expect } from 'vitest';
import {
  toCamelCase,
  toSnakeCase,
  transformResponse,
  toSnakeCaseWithExplicit,
} from '@/network/fieldMapper';

describe('fieldMapper', () => {
  describe('toCamelCase', () => {
    it('converts snake_case keys to camelCase', () => {
      const input = { user_name: 'Alice', created_at: '2024-01-01' };
      const result = toCamelCase<Record<string, unknown>>(input);
      expect(result).toEqual({ userName: 'Alice', createdAt: '2024-01-01' });
    });

    it('handles nested objects', () => {
      const input = { outer_key: { inner_key: 'value' } };
      const result = toCamelCase<Record<string, unknown>>(input);
      expect(result).toEqual({ outerKey: { innerKey: 'value' } });
    });
  });

  describe('toSnakeCase', () => {
    it('converts camelCase keys to snake_case', () => {
      const input = { userName: 'Alice', createdAt: '2024-01-01' };
      const result = toSnakeCase<Record<string, unknown>>(input);
      expect(result).toEqual({ user_name: 'Alice', created_at: '2024-01-01' });
    });
  });

  describe('explicit mapping: doc_id → id (knowledge endpoint)', () => {
    it('maps doc_id to id for knowledge docs', () => {
      const backendResponse = {
        doc_id: 'doc-123',
        status: 'completed',
        chunk_count: 5,
        error_msg: null,
      };
      const result = transformResponse(
        backendResponse,
        '/admin/v1/knowledge/docs/doc-123',
      ) as Record<string, unknown>;

      expect(result.id).toBe('doc-123');
      expect(result.status).toBe('completed');
      expect(result.chunkCount).toBe(5);
    });
  });

  describe('explicit mapping: primaryModel → model (config endpoint)', () => {
    it('maps primaryModel to model for config model endpoint', () => {
      const frontendRequest = {
        primaryModel: 'gpt-4',
        fallbackModel: 'gpt-3.5-turbo',
        temperature: 0.7,
      };
      const result = toSnakeCaseWithExplicit(
        frontendRequest,
        '/admin/v1/config/model',
      ) as Record<string, unknown>;

      expect(result.model).toBe('gpt-4');
      expect(result.fallback_model).toBe('gpt-3.5-turbo');
      expect(result.temperature).toBe(0.7);
      // primaryModel should not exist after explicit rename
      expect(result.primary_model).toBeUndefined();
    });
  });

  describe('structure adapter: overview adds aiResolutionRate', () => {
    it('computes aiResolutionRate from humanEscalationRate', () => {
      const backendResponse = {
        total_conversations: 100,
        human_transfer_count: 20,
        human_transfer_rate: 0.2,
        range: '7d',
      };
      const result = transformResponse(
        backendResponse,
        '/admin/v1/metrics/overview',
      ) as Record<string, unknown>;

      expect(result.aiResolutionRate).toBeCloseTo(0.8);
      expect(result.humanEscalationRate).toBeCloseTo(0.2);
      expect(result.totalConversations).toBe(100);
    });
  });

  describe('structure adapter: missed-queries unwraps array', () => {
    it('unwraps missed_queries from wrapper object', () => {
      const backendResponse = {
        missed_queries: [
          { query_prefix: 'how to', count: 15 },
          { query_prefix: 'what is', count: 8 },
        ],
        range: '7d',
      };
      const result = transformResponse(
        backendResponse,
        '/admin/v1/metrics/missed-queries',
      );

      expect(Array.isArray(result)).toBe(true);
      const arr = result as Record<string, unknown>[];
      expect(arr.length).toBe(2);
    });
  });

  describe('FormData passthrough', () => {
    it('returns FormData unchanged from toCamelCase', () => {
      const formData = new FormData();
      formData.append('file', 'test');
      const result = toCamelCase(formData);
      expect(result).toBe(formData);
    });

    it('returns FormData unchanged from toSnakeCase', () => {
      const formData = new FormData();
      formData.append('file', 'test');
      const result = toSnakeCase(formData);
      expect(result).toBe(formData);
    });
  });

  describe('null/undefined passthrough', () => {
    it('returns null as-is from toCamelCase', () => {
      expect(toCamelCase(null)).toBeNull();
    });

    it('returns undefined as-is from toCamelCase', () => {
      expect(toCamelCase(undefined)).toBeUndefined();
    });

    it('returns null as-is from toSnakeCase', () => {
      expect(toSnakeCase(null)).toBeNull();
    });

    it('returns undefined as-is from toSnakeCase', () => {
      expect(toSnakeCase(undefined)).toBeUndefined();
    });
  });
});
