// ─── Union Types ───────────────────────────────────────────────

export type SessionStatus = 'active' | 'hitl_pending' | 'hitl_active' | 'resolved';

export type ConnectionStatus = 'connected' | 'connecting' | 'disconnected';

export type DocStatus = 'pending' | 'processing' | 'completed' | 'failed';

export type MessageRole = 'user' | 'assistant' | 'human_agent';

// ─── Core Chat Types ──────────────────────────────────────────

export interface MediaAttachment {
  type: 'image' | 'audio';
  url: string;
  thumbnailUrl?: string;
  mimeType: string;
  sizeKb: number;
}

export interface ToolCall {
  id: string;
  name: string;
  arguments: string;
  result?: string;
}

export interface Message {
  id: string;
  threadId: string;
  role: MessageRole;
  content: string;
  mediaAttachments?: MediaAttachment[];
  toolCalls?: ToolCall[];
  createdAt: string;
  isOptimistic?: boolean;
  rating?: 'up' | 'down' | null;
  ratingReason?: string;
}

export interface ThreadMeta {
  id: string;
  title: string;
  lastMessageAt: string;
  messageCount: number;
}

// ─── Admin / Auth Types ───────────────────────────────────────

export interface AdminUser {
  id: string;
  email: string;
  tenantId: string;
  tenantName: string;
  role: string;
}

// ─── Knowledge Types ──────────────────────────────────────────

export interface KnowledgeDoc {
  id: string;
  filename: string;
  status: DocStatus;
  chunkCount: number;
  errorMsg?: string;
  createdAt: string;
  updatedAt: string;
}


// ─── HITL Types ───────────────────────────────────────────────

export interface HITLSession {
  sessionId: string;
  threadId: string;
  status: 'pending' | 'active' | 'resolved' | 'auto_escalated';
  adminUserId?: string;
  reason: string;
  unresolvedTurns: number;
  createdAt: string;
}

// ─── Config Types ─────────────────────────────────────────────

export interface PersonaConfig {
  systemPrompt: string;
  personaName: string;
  greeting: string;
}

export interface ModelConfig {
  primaryModel: string;
  fallbackModel: string;
  temperature: number;
}

export interface RateLimitConfig {
  tenantRps: number;
  userRps: number;
}

// ─── Metrics Types ────────────────────────────────────────────

export interface MetricsOverview {
  totalConversations: number;
  aiResolutionRate: number;
  humanEscalationRate: number;
  avgTtftMs: number;
  totalTokensUsed: number;
  totalTokensInput: number;
  totalTokensOutput: number;
  thumbUpRate?: number;
}

// ─── Sandbox Types ────────────────────────────────────────────

export interface TestCase {
  query: string;
  reference: string;
  contexts: string[];
}

export interface SandboxResult {
  testCase: TestCase;
  scores: {
    faithfulness: number;
    contextPrecision: number;
    contextRecall: number;
    answerRelevancy: number;
  };
  thresholds: Record<string, number>;
  passed: boolean;
}

// ─── Chat Widget Types ────────────────────────────────────────

export interface ChatWidgetProps {
  apiKey: string;
  theme?: 'light' | 'dark';
  position?: 'bottom-right' | 'bottom-left';
  lang?: 'zh-CN' | 'en';
  primaryColor?: string;
  bgColor?: string;
  logoUrl?: string;
}

// ─── Cache Types ──────────────────────────────────────────────

export interface CacheConfig {
  maxSizeBytes: number;
  maxMessages: number;
  maxThreads: number;
  ttlDays: number;
}

export interface CachedThread {
  id: string;
  meta: ThreadMeta;
  messages: Message[];
  cachedAt: number;
  sizeBytes: number;
}

// ─── Network Types ────────────────────────────────────────────

export interface SSEClientOptions {
  url: string;
  body: object;
  apiKey: string;
  onToken: (token: string, messageId?: string) => void;
  onDone: (messageId: string) => void;
  onError: (error: SSEError) => void;
}

export interface WSClientOptions {
  url: string;
  onMessage: (data: WSMessage) => void;
  onClose: () => void;
  onError: (error: Event) => void;
}

export interface WSMessage {
  type: string;
  data?: unknown;
}

export interface SSEError {
  code: string;
  message: string;
}
