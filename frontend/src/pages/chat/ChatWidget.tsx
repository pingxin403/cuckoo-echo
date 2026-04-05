import { useEffect, useState, useMemo, useCallback } from 'react';
import type { ChatWidgetProps, ConnectionStatus, MediaAttachment } from '@/types';
import { useSSE } from '@/hooks/useSSE';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useSessionStore } from '@/stores/sessionStore';
import { useChatStore } from '@/stores/chatStore';
import { analytics } from '@/lib/analytics';
import ChatInput from '@/pages/chat/ChatInput';
import MessageList from '@/pages/chat/MessageList';
import ThreadList from '@/pages/chat/ThreadList';
import HITLStatus from '@/pages/chat/HITLStatus';
import WaveformIndicator from '@/pages/chat/WaveformIndicator';

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '';

export default function ChatWidget({
  apiKey,
  theme = 'light',
  position = 'bottom-right',
  lang = 'zh-CN',
  primaryColor,
  bgColor,
  logoUrl,
}: ChatWidgetProps) {
  const [apiKeyError, setApiKeyError] = useState(false);
  const [isAsrProcessing, setIsAsrProcessing] = useState(false);

  const sessionStatus = useSessionStore((s) => s.status);
  const switchProtocol = useSessionStore((s) => s.switchProtocol);
  const sendMessage = useChatStore((s) => s.sendMessage);
  const appendToken = useChatStore((s) => s.appendToken);
  const finishStreaming = useChatStore((s) => s.finishStreaming);
  const isStreaming = useChatStore((s) => s.isStreaming);
  const setConnectionStatus = useChatStore((s) => s.setConnectionStatus);
  const loadThread = useChatStore((s) => s.loadThread);
  const activeThreadId = useSessionStore((s) => s.activeThreadId);

  const shouldUseWebSocket = sessionStatus === 'hitl_active' || sessionStatus === 'hitl_pending';

  useEffect(() => {
    switchProtocol(shouldUseWebSocket ? 'websocket' : 'sse');
  }, [shouldUseWebSocket, switchProtocol]);

  const sseUrl = `${API_BASE}/v1/chat/completions`;
  const {
    send: sseSend,
    connectionStatus: sseStatus,
    disconnect: disconnectSSE,
  } = useSSE({
    url: sseUrl,
    apiKey,
    onToken(token: string, _messageId?: string) { appendToken(token); },
    onDone(messageId: string) {
      finishStreaming(messageId);
      analytics.track('message_received', { thread_id: activeThreadId });
    },
    onError(error) {
      if (error.code === 'HTTP_ERROR' && error.message.includes('401')) setApiKeyError(true);
      // Reset streaming state on any SSE error so the UI isn't stuck
      finishStreaming('');
    },
    onReconnected() { if (activeThreadId) loadThread(activeThreadId); },
  });

  const handleSend = useCallback(
    (content: string, media?: MediaAttachment[]) => {
      analytics.track('message_sent', { thread_id: activeThreadId, has_media: !!media?.length, media_type: media?.[0]?.type });
      sendMessage(content, media);
      if (!shouldUseWebSocket) {
        sseSend({ thread_id: activeThreadId ?? undefined, messages: [{ role: 'user', content }] });
      }
    },
    [sendMessage, activeThreadId, sseSend, shouldUseWebSocket],
  );

  const wsUrl = shouldUseWebSocket ? `${API_BASE.replace(/^http/, 'ws')}/v1/chat/ws?api_key=${apiKey}` : '';
  const { connectionStatus: wsStatus } = useWebSocket({
    url: wsUrl,
    onMessage(msg) {
      if (msg.type === 'processing' && msg.data != null && (msg.data as { stage?: string }).stage === 'asr') setIsAsrProcessing(true);
      else if (msg.type === 'token' || msg.type === 'done') setIsAsrProcessing(false);
    },
  });

  useEffect(() => { if (shouldUseWebSocket) disconnectSSE(); }, [shouldUseWebSocket, disconnectSSE]);

  const connectionStatus: ConnectionStatus = shouldUseWebSocket ? wsStatus : sseStatus;
  useEffect(() => { setConnectionStatus(connectionStatus); }, [connectionStatus, setConnectionStatus]);

  const themeStyle = useMemo(
    () => ({
      '--ce-primary-color': primaryColor ?? (theme === 'dark' ? '#6366f1' : '#4f46e5'),
      '--ce-bg-color': bgColor ?? (theme === 'dark' ? '#1e1e2e' : '#ffffff'),
    }) as React.CSSProperties,
    [primaryColor, bgColor, theme],
  );

  if (apiKeyError) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50" style={themeStyle} role="alert">
        <div className="rounded-lg border border-red-200 bg-red-50 px-6 py-4 text-red-700">
          <p className="font-medium">配置错误</p>
          <p className="mt-1 text-sm">API Key 无效，请联系管理员</p>
        </div>
      </div>
    );
  }

  return (
    <div
      className="flex h-screen flex-col bg-white"
      style={themeStyle}
      data-theme={theme}
      data-position={position}
      data-lang={lang}
    >
      {/* Header bar */}
      <header className="flex h-12 shrink-0 items-center justify-between border-b border-gray-200 bg-white px-4">
        <div className="flex items-center gap-2">
          {logoUrl ? (
            <img src={logoUrl} alt="Logo" className="h-7" />
          ) : (
            <span className="text-sm font-semibold text-gray-800">Cuckoo-Echo</span>
          )}
        </div>
        <div
          className="flex items-center gap-1.5"
          aria-live="polite"
          aria-label={connectionStatus === 'connected' ? '已连接' : connectionStatus === 'connecting' ? '连接中…' : '已断开'}
        >
          <span
            className="inline-block h-2 w-2 rounded-full"
            style={{
              backgroundColor: connectionStatus === 'connected' ? '#22c55e' : connectionStatus === 'connecting' ? '#f59e0b' : '#ef4444',
            }}
          />
          <span className="text-xs text-gray-500">
            {connectionStatus === 'connected' ? '已连接' : connectionStatus === 'connecting' ? '连接中…' : '已断开'}
          </span>
        </div>
      </header>

      {/* Main content */}
      <div className="flex min-h-0 flex-1">
        {/* Thread sidebar */}
        <aside
          className="w-56 shrink-0 border-r border-gray-200 bg-gray-50 overflow-y-auto"
          aria-label="会话列表"
        >
          <ThreadList />
        </aside>

        {/* Chat area */}
        <div className="flex min-w-0 flex-1 flex-col bg-white">
          <HITLStatus />
          {isAsrProcessing && (
            <div className="mx-4 my-2">
              <WaveformIndicator />
            </div>
          )}
          <MessageList />
          <ChatInput onSend={handleSend} disabled={isStreaming} />
        </div>
      </div>
    </div>
  );
}
