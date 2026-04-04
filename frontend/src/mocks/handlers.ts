import { http, HttpResponse } from 'msw';
import type {
  AdminUser,
  KnowledgeDoc,
  HITLSession,
  PersonaConfig,
  ModelConfig,
  RateLimitConfig,
  MetricsOverview,
  SandboxResult,
  Message,
} from '@/types';

// ─── Mock Data ─────────────────────────────────────────────────

const mockUser: AdminUser = {
  id: 'usr_001',
  email: 'admin@example.com',
  tenantId: 'tenant_001',
  tenantName: 'Demo Tenant',
  role: 'admin',
};

const mockMessages: Message[] = [
  {
    id: 'msg_001',
    threadId: 'thread_001',
    role: 'user',
    content: 'Hello, I need help with my order.',
    createdAt: '2024-01-15T10:00:00Z',
  },
  {
    id: 'msg_002',
    threadId: 'thread_001',
    role: 'assistant',
    content: 'Sure! Could you provide your order number?',
    createdAt: '2024-01-15T10:00:05Z',
  },
];

const mockDocuments: KnowledgeDoc[] = [
  {
    id: 'doc_001',
    filename: 'product-faq.pdf',
    status: 'completed',
    chunkCount: 42,
    createdAt: '2024-01-10T08:00:00Z',
    updatedAt: '2024-01-10T08:05:00Z',
  },
  {
    id: 'doc_002',
    filename: 'return-policy.docx',
    status: 'processing',
    chunkCount: 0,
    createdAt: '2024-01-14T12:00:00Z',
    updatedAt: '2024-01-14T12:00:00Z',
  },
];

const mockHitlSessions: HITLSession[] = [
  {
    sessionId: 'hitl_001',
    threadId: 'thread_002',
    status: 'pending',
    reason: 'Low confidence score',
    unresolvedTurns: 3,
    createdAt: '2024-01-15T09:30:00Z',
  },
];

const mockPersona: PersonaConfig = {
  systemPrompt: 'You are a helpful customer service assistant.',
  personaName: 'Cuckoo Bot',
  greeting: 'Hi! How can I help you today?',
};

const mockModelConfig: ModelConfig = {
  primaryModel: 'gpt-4o',
  fallbackModel: 'gpt-4o-mini',
  temperature: 0.7,
};

const mockRateLimitConfig: RateLimitConfig = {
  tenantRps: 100,
  userRps: 10,
};

const mockMetrics: MetricsOverview = {
  totalConversations: 1250,
  aiResolutionRate: 0.82,
  humanEscalationRate: 0.18,
  avgTtftMs: 320,
  totalTokensUsed: 2500000,
  totalTokensInput: 1500000,
  totalTokensOutput: 1000000,
  thumbUpRate: 0.76,
};

// ─── Handlers ──────────────────────────────────────────────────

export const handlers = [
  // Auth
  http.post('*/admin/v1/auth/login', async ({ request }) => {
    const body = (await request.json()) as { email: string; password: string };
    if (body.email === 'admin@example.com' && body.password === 'password') {
      // Minimal mock JWT (header.payload.signature)
      const payload = btoa(
        JSON.stringify({
          sub: mockUser.id,
          email: mockUser.email,
          tenant_id: mockUser.tenantId,
          tenant_name: mockUser.tenantName,
          role: mockUser.role,
          exp: Math.floor(Date.now() / 1000) + 3600,
        }),
      );
      return HttpResponse.json({ access_token: `eyJ.${payload}.sig` });
    }
    return new HttpResponse(null, { status: 401 });
  }),

  http.post('*/admin/v1/auth/refresh', () => {
    const payload = btoa(
      JSON.stringify({
        sub: mockUser.id,
        email: mockUser.email,
        tenant_id: mockUser.tenantId,
        tenant_name: mockUser.tenantName,
        role: mockUser.role,
        exp: Math.floor(Date.now() / 1000) + 3600,
      }),
    );
    return HttpResponse.json({ access_token: `eyJ.${payload}.sig` });
  }),

  http.post('*/admin/v1/auth/logout', () => {
    return new HttpResponse(null, { status: 204 });
  }),

  // Chat — threads
  http.get('*/v1/threads/:threadId', () => {
    return HttpResponse.json({ messages: mockMessages });
  }),

  // Knowledge
  http.get('*/admin/v1/knowledge/docs', () => {
    return HttpResponse.json(mockDocuments);
  }),

  http.post('*/admin/v1/knowledge/docs', () => {
    const newDoc: KnowledgeDoc = {
      id: `doc_${Date.now()}`,
      filename: 'new-upload.pdf',
      status: 'pending',
      chunkCount: 0,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    return HttpResponse.json(newDoc, { status: 201 });
  }),

  http.delete('*/admin/v1/knowledge/docs/:id', () => {
    return new HttpResponse(null, { status: 204 });
  }),

  http.post('*/admin/v1/knowledge/docs/:id/retry', () => {
    return HttpResponse.json({ status: 'pending' });
  }),

  // HITL
  http.post('*/admin/v1/hitl/:sessionId/take', ({ params }) => {
    const session: HITLSession = {
      ...mockHitlSessions[0],
      sessionId: params.sessionId as string,
      status: 'active',
      adminUserId: mockUser.id,
    };
    return HttpResponse.json(session);
  }),

  http.post('*/admin/v1/hitl/:sessionId/end', () => {
    return new HttpResponse(null, { status: 204 });
  }),

  // Config
  http.get('*/admin/v1/config', () => {
    return HttpResponse.json({
      persona: mockPersona,
      model: mockModelConfig,
      rateLimit: mockRateLimitConfig,
    });
  }),

  http.put('*/admin/v1/config/persona', () => {
    return new HttpResponse(null, { status: 204 });
  }),

  http.put('*/admin/v1/config/model', () => {
    return new HttpResponse(null, { status: 204 });
  }),

  http.put('*/admin/v1/config/rate-limit', () => {
    return new HttpResponse(null, { status: 204 });
  }),

  http.post('*/admin/v1/cache/clear', () => {
    return new HttpResponse(null, { status: 204 });
  }),

  // Metrics
  http.get('*/admin/v1/metrics/overview', () => {
    return HttpResponse.json(mockMetrics);
  }),

  http.get('*/admin/v1/metrics/tokens', () => {
    return HttpResponse.json({
      totalTokens: mockMetrics.totalTokensUsed,
      totalMessages: 8500,
    });
  }),

  http.get('*/admin/v1/metrics/missed-queries', () => {
    return HttpResponse.json([
      { query: 'How to cancel subscription?', count: 45 },
      { query: 'Refund policy for digital goods', count: 32 },
    ]);
  }),

  // Sandbox
  http.post('*/admin/v1/sandbox/run', async ({ request }) => {
    const body = (await request.json()) as { testCases: { query: string; reference: string; contexts: string[] }[] };
    const results: SandboxResult[] = (body.testCases ?? []).map((tc) => ({
      testCase: tc,
      scores: {
        faithfulness: 0.85,
        contextPrecision: 0.9,
        contextRecall: 0.78,
        answerRelevancy: 0.88,
      },
      thresholds: {
        faithfulness: 0.7,
        contextPrecision: 0.7,
        contextRecall: 0.7,
        answerRelevancy: 0.7,
      },
      passed: true,
    }));
    return HttpResponse.json(results);
  }),

  // Feedback
  http.post('*/v1/feedback', () => {
    return new HttpResponse(null, { status: 204 });
  }),
];
