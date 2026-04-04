import camelcaseKeys from 'camelcase-keys';
import snakecaseKeys from 'snakecase-keys';

// ─── Generic Conversion ────────────────────────────────────────

export function toCamelCase<T>(obj: unknown): T {
  if (obj == null || typeof obj !== 'object' || obj instanceof FormData) return obj as T;
  return camelcaseKeys(obj as Record<string, unknown>, { deep: true }) as T;
}

export function toSnakeCase<T>(obj: unknown): T {
  if (obj == null || typeof obj !== 'object' || obj instanceof FormData) return obj as T;
  return snakecaseKeys(obj as Record<string, unknown>, { deep: true }) as T;
}

// ─── Explicit Field Mapping Rules ──────────────────────────────

/** 后端字段 → 前端字段（非标准映射） */
export const EXPLICIT_BACKEND_TO_FRONTEND: Record<string, Record<string, string>> = {
  '/admin/v1/knowledge/docs/*': {
    doc_id: 'id',
  },
  '/admin/v1/metrics/overview': {
    human_transfer_rate: 'humanEscalationRate',
  },
  '/admin/v1/metrics/missed-queries': {
    query_prefix: 'query',
  },
  '/admin/v1/auth/login': {
    admin_user_id: 'id',
  },
};

/** 前端字段 → 后端字段（非标准映射） */
export const EXPLICIT_FRONTEND_TO_BACKEND: Record<string, Record<string, string>> = {
  '/admin/v1/config/model': {
    primaryModel: 'model',
  },
};

// ─── Explicit Field Rename Helper ──────────────────────────────

function applyExplicitRenames(
  obj: Record<string, unknown>,
  renames: Record<string, string>,
): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(obj)) {
    const newKey = renames[key] ?? key;
    result[newKey] = value;
  }
  return result;
}

// ─── Endpoint Matching ─────────────────────────────────────────

function findMatchingRules<T>(
  endpoint: string,
  ruleTable: Record<string, T>,
): T | undefined {
  // Exact match first
  if (ruleTable[endpoint]) return ruleTable[endpoint];

  // Wildcard match (e.g., '/admin/v1/knowledge/docs/*')
  for (const pattern of Object.keys(ruleTable)) {
    if (pattern.endsWith('/*')) {
      const prefix = pattern.slice(0, -1); // remove trailing '*'
      if (endpoint.startsWith(prefix)) return ruleTable[pattern];
    }
  }
  return undefined;
}

// ─── Structure Adapters ────────────────────────────────────────

const STRUCTURE_ADAPTERS: Record<string, (data: unknown) => unknown> = {
  '/admin/v1/metrics/overview': (data) => {
    const d = data as Record<string, unknown>;
    return {
      ...d,
      aiResolutionRate: 1 - (Number(d.humanEscalationRate ?? d.human_transfer_rate) || 0),
      avgTtftMs: d.avgTtftMs ?? 0,
      totalTokensUsed: d.totalTokensUsed ?? 0,
      totalTokensInput: d.totalTokensInput ?? 0,
      totalTokensOutput: d.totalTokensOutput ?? 0,
    };
  },
  '/admin/v1/metrics/missed-queries': (data) => {
    const d = data as Record<string, unknown>;
    return (d.missed_queries ?? d.missedQueries ?? data) as unknown;
  },
  '/admin/v1/knowledge/docs/*': (data) => {
    const d = data as Record<string, unknown>;
    // Rename doc_id → id if still present after explicit mapping
    if ('docId' in d && !('id' in d)) {
      const { docId, ...rest } = d;
      return { id: docId, ...rest };
    }
    return d;
  },
};

// ─── Combined Transform Functions ──────────────────────────────

/**
 * Transform a backend response for frontend consumption.
 * Pipeline: explicit field renames → generic snake→camel → structure adapter
 */
export function transformResponse(data: unknown, endpoint: string): unknown {
  if (data == null || typeof data !== 'object') return data;

  // Handle arrays: apply transform to each element
  if (Array.isArray(data)) {
    return data.map((item) => transformResponse(item, endpoint));
  }

  let result = data as Record<string, unknown>;

  // Step 1: Apply explicit backend→frontend field renames
  const explicitRules = findMatchingRules(endpoint, EXPLICIT_BACKEND_TO_FRONTEND);
  if (explicitRules) {
    result = applyExplicitRenames(result, explicitRules);
  }

  // Step 2: Generic snake_case → camelCase
  result = toCamelCase<Record<string, unknown>>(result);

  // Step 3: Apply structure adapter
  const adapter = findMatchingRules(endpoint, STRUCTURE_ADAPTERS);
  if (adapter) {
    return adapter(result);
  }

  return result;
}

/**
 * Transform a frontend request body for backend consumption.
 * Pipeline: explicit field renames → generic camel→snake
 */
export function toSnakeCaseWithExplicit(data: unknown, endpoint: string): unknown {
  if (data == null || typeof data !== 'object' || data instanceof FormData) return data;

  // Handle arrays: apply transform to each element
  if (Array.isArray(data)) {
    return data.map((item) => toSnakeCaseWithExplicit(item, endpoint));
  }

  let result = data as Record<string, unknown>;

  // Step 1: Apply explicit frontend→backend field renames
  const explicitRules = findMatchingRules(endpoint, EXPLICIT_FRONTEND_TO_BACKEND);
  if (explicitRules) {
    result = applyExplicitRenames(result, explicitRules);
  }

  // Step 2: Generic camelCase → snake_case
  return toSnakeCase(result);
}
