import type { Message, MessageRole } from '@/types';

/**
 * LangGraph message format (as stored in backend checkpoints).
 */
export interface LangGraphMessage {
  type: 'human' | 'ai' | 'tool';
  content: string;
  id?: string;
  tool_calls?: { id: string; name: string; args: Record<string, unknown> }[];
  additional_kwargs?: Record<string, unknown>;
}

const ROLE_MAP: Record<string, MessageRole> = {
  human: 'user',
  ai: 'assistant',
};

/**
 * Convert a LangGraph message to the frontend Message type.
 */
export function convertLangGraphMessage(
  msg: LangGraphMessage,
  threadId: string,
): Message {
  return {
    id: msg.id ?? crypto.randomUUID(),
    threadId,
    role: ROLE_MAP[msg.type] ?? 'assistant',
    content: msg.content,
    toolCalls: msg.tool_calls?.map((tc) => ({
      id: tc.id,
      name: tc.name,
      arguments: JSON.stringify(tc.args),
    })),
    createdAt: new Date().toISOString(),
  };
}

/**
 * Convert an array of LangGraph messages to frontend Message[].
 * Filters out 'tool' type messages (not displayed in UI).
 */
export function convertLangGraphMessages(
  msgs: LangGraphMessage[],
  threadId: string,
): Message[] {
  return msgs
    .filter((m) => m.type !== 'tool')
    .map((m) => convertLangGraphMessage(m, threadId));
}
