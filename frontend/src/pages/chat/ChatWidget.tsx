import { useEffect, useState, useMemo, useCallback } from 'react';
import type { ChatWidgetProps, ConnectionStatus } from '@/types';
import { useSSE } from '@/hooks/useSSE';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useSessionStore } from '@/stores/sessionStore';
import { useChatStore } from '@/stores/chatStore';
import ChatInput from '@/pages/chat/ChatInput';
import ThreadList from '@/pages/chat/ThreadList';
import HITLStatus from '@/pages/chat/HITLStatus';

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '';

/**
 * ChatWidget — C-端聊天主组件
 *
 * Manages SSE ↔ WebSocket protocol switching based on session status,
 * renders ThreadList sidebar + MessageList + ChatInput (placeholders for now),
 * and applies CSS variable theming.
 */
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

  // ── Session store ──
  const sessionStatus = useSessionStore((s) => s.status);
  const switchProtocol = useSessionStore((s) => s.switchProtocol);

  // ── Chat store ──
  const sendMessage = useChatStore((s) => s.sendMessage);
  const isStreaming = useChatStore((s) => s.isStreaming);
  const setConnectionStatus = useChatStore((s) => s.setConnectionStatus);

  const handleSend = useCallback(
    (content: string) => {
      sendMessage(content);
    },
    [sendMessage],
  );

  // ── Determine active protocol from session status ──
  const shouldUseWebSocket =
    sessionStatus === 'hitl_active' || sessionStatus === 'hitl_pending';

  // Sync protocol to session store
  useEffect(() => {
    switchProtocol(shouldUseWebSocket ? 'websocket' : 'sse');
  }, [shouldUseWebSocket, switchProtocol]);

  // ── SSE hook (active when NOT in HITL mode) ──
  // TODO(SSE-reconciliation): After SSE reconnects, the useSSE hook's
  // reconnection flow should call chatStore.reconcileMessages() with the
  // latest server messages to compensate for any messages missed during
  // the disconnection window. This is handled by the SSE reconnection
  // flow in sseClient.ts (exponential backoff → reconnect → fetch latest
  // thread → reconcile). See requirement 1.6.
  const sseUrl = `${API_BASE}/v1/chat/completions`;
  const {
    connectionStatus: sseStatus,
    disconnect: disconnectSSE,
  } = useSSE({
    url: sseUrl,
    apiKey,
    onError(error) {
      // 401 from SSE means invalid API key
      if (error.code === 'HTTP_ERROR' && error.message.includes('401')) {
        setApiKeyError(true);
      }
    },
  });

  // ── WebSocket hook (active when in HITL mode) ──
  const wsUrl = shouldUseWebSocket
    ? `${API_BASE.replace(/^http/, 'ws')}/v1/chat/ws?api_key=${apiKey}`
    : '';
  const { connectionStatus: wsStatus } = useWebSocket({
    url: wsUrl,
  });

  // Disconnect SSE when switching to WebSocket
  useEffect(() => {
    if (shouldUseWebSocket) {
      disconnectSSE();
    }
  }, [shouldUseWebSocket, disconnectSSE]);

  // ── Unified connection status ──
  const connectionStatus: ConnectionStatus = shouldUseWebSocket
    ? wsStatus
    : sseStatus;

  // Sync to chat store
  useEffect(() => {
    setConnectionStatus(connectionStatus);
  }, [connectionStatus, setConnectionStatus]);

  // ── CSS variable theming ──
  const themeStyle = useMemo(
    () => ({
      '--ce-primary-color': primaryColor ?? (theme === 'dark' ? '#6366f1' : '#4f46e5'),
      '--ce-bg-color': bgColor ?? (theme === 'dark' ? '#1e1e2e' : '#ffffff'),
    }) as React.CSSProperties,
    [primaryColor, bgColor, theme],
  );

  // ── API Key invalid → show error ──
  if (apiKeyError) {
    return (
      <div
        className="ce-widget ce-widget--error"
        style={themeStyle}
        data-theme={theme}
        data-position={position}
        data-lang={lang}
        role="alert"
      >
        <p>配置错误，请联系管理员</p>
      </div>
    );
  }

  // ── Main chat UI ──
  return (
    <div
      className="ce-widget"
      style={themeStyle}
      data-theme={theme}
      data-position={position}
      data-lang={lang}
    >
      {/* Connection status indicator */}
      <div
        className="ce-connection-status"
        aria-live="polite"
        aria-label={
          connectionStatus === 'connected'
            ? '已连接'
            : connectionStatus === 'connecting'
              ? '连接中…'
              : '已断开'
        }
      >
        <span
          className="ce-status-dot"
          data-status={connectionStatus}
          style={{
            display: 'inline-block',
            width: 8,
            height: 8,
            borderRadius: '50%',
            marginRight: 6,
            backgroundColor:
              connectionStatus === 'connected'
                ? '#22c55e'
                : connectionStatus === 'connecting'
                  ? '#f59e0b'
                  : '#ef4444',
          }}
        />
        <span className="ce-status-text" style={{ fontSize: 12 }}>
          {connectionStatus === 'connected'
            ? '已连接'
            : connectionStatus === 'connecting'
              ? '连接中…'
              : '已断开'}
        </span>
      </div>

      {/* Logo */}
      {logoUrl && (
        <img
          src={logoUrl}
          alt="Logo"
          className="ce-logo"
          style={{ height: 32, marginBottom: 8 }}
        />
      )}

      <div className="ce-layout" style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* ThreadList sidebar */}
        <aside
          className="ce-thread-list"
          style={{
            width: 220,
            borderRight: '1px solid #e5e7eb',
            overflowY: 'auto',
          }}
          aria-label="会话列表"
        >
          <ThreadList />
        </aside>

        {/* Main chat area */}
        <div className="ce-main" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          {/* HITL status banner */}
          <HITLStatus />

          {/* MessageList — placeholder */}
          <div
            className="ce-message-list"
            style={{ flex: 1, overflowY: 'auto', padding: 16 }}
            aria-label="消息列表"
          >
            <div style={{ color: '#9ca3af', fontSize: 13 }}>消息列表（待实现）</div>
          </div>

          {/* ChatInput */}
          <ChatInput onSend={handleSend} disabled={isStreaming} />
        </div>
      </div>
    </div>
  );
}
