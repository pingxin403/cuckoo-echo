import { create } from 'zustand';
import type {
  KnowledgeDoc,
  DocStatus,
  HITLSession,
  PersonaConfig,
  ModelConfig,
  RateLimitConfig,
  MetricsOverview,
  TestCase,
  SandboxResult,
} from '@/types';
import apiClient from '@/network/axios';

// ─── 1. Knowledge Store ────────────────────────────────────────

interface KnowledgeState {
  documents: KnowledgeDoc[];
  docFilter: { search: string; status: DocStatus | 'all' };
  isLoading: boolean;
  fetchDocuments: () => Promise<void>;
  uploadDocument: (file: File) => Promise<void>;
  deleteDocument: (id: string) => Promise<void>;
  setDocFilter: (filter: Partial<KnowledgeState['docFilter']>) => void;
}

export const useKnowledgeStore = create<KnowledgeState>((set, get) => ({
  documents: [],
  docFilter: { search: '', status: 'all' },
  isLoading: false,

  async fetchDocuments() {
    set({ isLoading: true });
    try {
      const res = await apiClient.get<KnowledgeDoc[]>('/admin/v1/knowledge/docs');
      set({ documents: res.data });
    } finally {
      set({ isLoading: false });
    }
  },

  async uploadDocument(file: File) {
    const formData = new FormData();
    formData.append('file', file);
    await apiClient.post('/admin/v1/knowledge/docs', formData);
    await get().fetchDocuments();
  },

  async deleteDocument(id: string) {
    await apiClient.delete(`/admin/v1/knowledge/docs/${id}`);
    set((s) => ({ documents: s.documents.filter((d) => d.id !== id) }));
  },

  setDocFilter(filter) {
    set((s) => ({ docFilter: { ...s.docFilter, ...filter } }));
  },
}));

// ─── 2. HITL Store ─────────────────────────────────────────────

interface HitlState {
  hitlSessions: HITLSession[];
  activeHitlSession: HITLSession | null;
  takeHitlSession: (sessionId: string) => Promise<void>;
  endHitlSession: (sessionId: string) => Promise<void>;
  setHitlSessions: (sessions: HITLSession[]) => void;
  setActiveHitlSession: (session: HITLSession | null) => void;
}

export const useHitlStore = create<HitlState>((set) => ({
  hitlSessions: [],
  activeHitlSession: null,

  async takeHitlSession(sessionId: string) {
    const res = await apiClient.post<HITLSession>(`/admin/v1/hitl/${sessionId}/take`);
    set((s) => ({
      activeHitlSession: res.data,
      hitlSessions: s.hitlSessions.map((sess) =>
        sess.sessionId === sessionId ? res.data : sess,
      ),
    }));
  },

  async endHitlSession(sessionId: string) {
    await apiClient.post(`/admin/v1/hitl/${sessionId}/end`);
    set((s) => ({
      activeHitlSession:
        s.activeHitlSession?.sessionId === sessionId ? null : s.activeHitlSession,
      hitlSessions: s.hitlSessions.map((sess) =>
        sess.sessionId === sessionId ? { ...sess, status: 'resolved' as const } : sess,
      ),
    }));
  },

  setHitlSessions(sessions) {
    set({ hitlSessions: sessions });
  },

  setActiveHitlSession(session) {
    set({ activeHitlSession: session });
  },
}));

// ─── 3. Config Store ───────────────────────────────────────────

interface ConfigState {
  persona: PersonaConfig | null;
  modelConfig: ModelConfig | null;
  rateLimitConfig: RateLimitConfig | null;
  fetchConfig: () => Promise<void>;
  savePersona: (config: PersonaConfig) => Promise<void>;
  saveModelConfig: (config: ModelConfig) => Promise<void>;
  saveRateLimitConfig: (config: RateLimitConfig) => Promise<void>;
}

export const useConfigStore = create<ConfigState>((set) => ({
  persona: null,
  modelConfig: null,
  rateLimitConfig: null,

  async fetchConfig() {
    const res = await apiClient.get<{
      persona: PersonaConfig;
      model: ModelConfig;
      rateLimit: RateLimitConfig;
    }>('/admin/v1/config');
    set({
      persona: res.data.persona,
      modelConfig: res.data.model,
      rateLimitConfig: res.data.rateLimit,
    });
  },

  async savePersona(config) {
    await apiClient.put('/admin/v1/config/persona', config);
    set({ persona: config });
  },

  async saveModelConfig(config) {
    await apiClient.put('/admin/v1/config/model', config);
    set({ modelConfig: config });
  },

  async saveRateLimitConfig(config) {
    await apiClient.put('/admin/v1/config/rate-limit', config);
    set({ rateLimitConfig: config });
  },
}));

// ─── 4. Metrics Store ──────────────────────────────────────────

interface MetricsState {
  metricsOverview: MetricsOverview | null;
  metricsPeriod: '1d' | '7d' | '30d';
  isLoading: boolean;
  fetchMetrics: (period?: '1d' | '7d' | '30d') => Promise<void>;
  setMetricsPeriod: (period: '1d' | '7d' | '30d') => void;
}

export const useMetricsStore = create<MetricsState>((set, get) => ({
  metricsOverview: null,
  metricsPeriod: '7d',
  isLoading: false,

  async fetchMetrics(period) {
    const p = period ?? get().metricsPeriod;
    set({ isLoading: true, metricsPeriod: p });
    try {
      const res = await apiClient.get<MetricsOverview>(
        `/admin/v1/metrics/overview?period=${p}`,
      );
      set({ metricsOverview: res.data });
    } finally {
      set({ isLoading: false });
    }
  },

  setMetricsPeriod(period) {
    set({ metricsPeriod: period });
  },
}));

// ─── 5. Sandbox Store ──────────────────────────────────────────

interface SandboxState {
  sandboxResults: SandboxResult[];
  isRunning: boolean;
  runSandbox: (testCases: TestCase[]) => Promise<void>;
  clearResults: () => void;
}

export const useSandboxStore = create<SandboxState>((set) => ({
  sandboxResults: [],
  isRunning: false,

  async runSandbox(testCases) {
    set({ isRunning: true });
    try {
      const res = await apiClient.post<SandboxResult[]>(
        '/admin/v1/sandbox/run',
        { testCases },
      );
      set({ sandboxResults: res.data });
    } finally {
      set({ isRunning: false });
    }
  },

  clearResults() {
    set({ sandboxResults: [] });
  },
}));
