import { useState, useEffect, useCallback, useRef } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useHitlStore } from '@/stores/adminStore';
import { Skeleton } from '@/components/Skeleton';
import { showToast } from '@/components/Toast';
import { analytics } from '@/lib/analytics';
import apiClient from '@/network/axios';
import type { HITLSession, WSMessage, Message } from '@/types';

const WS_URL = `${(import.meta.env.VITE_WS_BASE_URL as string | undefined) ?? 'ws://localhost:8002'}/admin/v1/ws/hitl`;

const STATUS_LABELS: Record<HITLSession['status'], string> = {
  pending: '待处理',
  active: '处理中',
  resolved: '已解决',
  auto_escalated: '自动升级',
};

const STATUS_COLORS: Record<HITLSession['status'], string> = {
  pending: 'bg-red-100 text-red-700',
  active: 'bg-blue-100 text-blue-700',
  resolved: 'bg-green-100 text-green-700',
  auto_escalated: 'bg-yellow-100 text-yellow-700',
};

export default function HITLPanel() {
  const {
    hitlSessions,
    activeHitlSession,
    setHitlSessions,
    setActiveHitlSession,
    takeHitlSession,
    endHitlSession,
  } = useHitlStore();

  const [isLoading, setIsLoading] = useState(true);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [userInteracted, setUserInteracted] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Track user interaction for sound policy
  useEffect(() => {
    const handler = () => setUserInteracted(true);
    document.addEventListener('click', handler, { once: true });
    return () => document.removeEventListener('click', handler);
  }, []);

  // Play notification sound
  const playNotification = useCallback(() => {
    if (!userInteracted || isMuted) return;
    try {
      if (!audioRef.current) {
        const ctx = new AudioContext();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.frequency.value = 800;
        gain.gain.value = 0.3;
        osc.start();
        osc.stop(ctx.currentTime + 0.15);
      }
    } catch {
      // Ignore audio errors
    }
  }, [userInteracted, isMuted]);

  // WebSocket message handler
  const handleWsMessage = useCallback(
    (msg: WSMessage) => {
      if (msg.type === 'hitl_request' || msg.type === 'hitl_update') {
        const session = msg.data as HITLSession;
        setHitlSessions(
          hitlSessions.some((s) => s.sessionId === session.sessionId)
            ? hitlSessions.map((s) => (s.sessionId === session.sessionId ? session : s))
            : [...hitlSessions, session],
        );
        if (session.status === 'pending') {
          playNotification();
        }
      } else if (msg.type === 'hitl_message') {
        const message = msg.data as Message;
        if (activeHitlSession && message.threadId === activeHitlSession.threadId) {
          setMessages((prev) => [...prev, message]);
        }
      }
    },
    [hitlSessions, setHitlSessions, playNotification, activeHitlSession],
  );

  const { connectionStatus } = useWebSocket({
    url: WS_URL,
    onMessage: handleWsMessage,
  });

  // Initial load
  useEffect(() => {
    const load = async () => {
      try {
        const res = await apiClient.get<HITLSession[]>('/admin/v1/hitl/sessions');
        setHitlSessions(res.data);
      } catch {
        showToast('error', '加载介入会话失败');
      } finally {
        setIsLoading(false);
      }
    };
    load();
  }, [setHitlSessions]);

  // Auto-scroll messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleTake = async (sessionId: string) => {
    try {
      await takeHitlSession(sessionId);
      const session = useHitlStore.getState().activeHitlSession;
      if (session) {
        analytics.track('hitl_requested', { thread_id: session.threadId, reason: session.reason });
        const res = await apiClient.get<Message[]>(`/v1/threads/${session.threadId}`);
        setMessages(res.data);
      }
      showToast('success', '已接管会话');
    } catch {
      showToast('error', '接管失败，请重试');
    }
  };

  const handleEnd = async () => {
    if (!activeHitlSession) return;
    try {
      await endHitlSession(activeHitlSession.sessionId);
      setMessages([]);
      showToast('success', '已结束介入');
    } catch {
      showToast('error', '结束介入失败');
    }
  };

  const handleSend = async () => {
    if (!inputText.trim() || !activeHitlSession || isSending) return;
    setIsSending(true);
    try {
      const res = await apiClient.post<Message>(
        `/admin/v1/hitl/${activeHitlSession.sessionId}/message`,
        { content: inputText.trim() },
      );
      setMessages((prev) => [...prev, res.data]);
      setInputText('');
    } catch {
      showToast('error', '发送失败');
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const pendingCount = hitlSessions.filter((s) => s.status === 'pending').length;

  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton variant="text" />
        <Skeleton variant="list" />
        <Skeleton variant="list" />
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-0" aria-label="人工介入面板">
      {/* Session list */}
      <div className="w-80 flex-shrink-0 border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold">介入会话</h2>
            {pendingCount > 0 && (
              <span className="inline-flex items-center justify-center w-5 h-5 text-xs font-bold text-white bg-red-500 rounded-full" aria-label={`${pendingCount} 个待处理`}>
                {pendingCount}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {connectionStatus !== 'connected' && (
              <span className="text-xs text-yellow-600" role="status">连接中…</span>
            )}
            <button
              onClick={() => setIsMuted(!isMuted)}
              className="p-1 rounded hover:bg-gray-100 text-gray-500"
              aria-label={isMuted ? '取消静音' : '静音'}
              title={isMuted ? '取消静音' : '静音'}
            >
              {isMuted ? (
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2" /></svg>
              ) : (
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072M18.364 5.636a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" /></svg>
              )}
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {hitlSessions.length === 0 ? (
            <p className="p-4 text-sm text-gray-500 text-center">暂无介入会话</p>
          ) : (
            hitlSessions.map((session) => (
              <button
                key={session.sessionId}
                onClick={() => {
                  if (session.status === 'pending') {
                    handleTake(session.sessionId);
                  } else if (session.status === 'active') {
                    setActiveHitlSession(session);
                    apiClient.get<Message[]>(`/v1/threads/${session.threadId}`).then((res) => setMessages(res.data)).catch(() => showToast('error', '加载对话失败'));
                  } else {
                    setActiveHitlSession(session);
                    setMessages([]);
                  }
                }}
                className={`w-full text-left p-3 border-b border-gray-100 hover:bg-gray-50 transition-colors ${
                  activeHitlSession?.sessionId === session.sessionId ? 'bg-blue-50' : ''
                }`}
                aria-label={`会话 ${session.sessionId.slice(0, 8)}`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-gray-900 truncate">
                    {session.sessionId.slice(0, 8)}…
                  </span>
                  <span className={`text-xs px-1.5 py-0.5 rounded ${STATUS_COLORS[session.status]}`}>
                    {STATUS_LABELS[session.status]}
                  </span>
                </div>
                <p className="text-xs text-gray-500 truncate">原因: {session.reason}</p>
                <div className="flex items-center justify-between mt-1">
                  <span className="text-xs text-gray-400">未解决: {session.unresolvedTurns} 轮</span>
                  {session.adminUserId && (
                    <span className="text-xs text-gray-400">处理人: {session.adminUserId.slice(0, 6)}</span>
                  )}
                </div>
                {session.status === 'pending' && (
                  <span className="mt-1 inline-block text-xs text-red-600 font-medium">点击接管</span>
                )}
              </button>
            ))
          )}
        </div>
      </div>

      {/* Conversation area */}
      <div className="flex-1 flex flex-col min-w-0">
        {activeHitlSession ? (
          <>
            {/* Header */}
            <div className="p-4 border-b border-gray-200 flex items-center justify-between">
              <div>
                <h3 className="font-medium text-gray-900">
                  会话 {activeHitlSession.sessionId.slice(0, 8)}…
                </h3>
                <p className="text-xs text-gray-500">
                  {STATUS_LABELS[activeHitlSession.status]} · {activeHitlSession.reason}
                </p>
              </div>
              {activeHitlSession.status === 'active' && (
                <button
                  onClick={handleEnd}
                  className="px-3 py-1.5 text-sm bg-orange-500 text-white rounded hover:bg-orange-600 transition-colors"
                  aria-label="结束介入"
                >
                  结束介入
                </button>
              )}
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[70%] rounded-lg px-3 py-2 text-sm ${
                      msg.role === 'user'
                        ? 'bg-blue-500 text-white'
                        : msg.role === 'human_agent'
                          ? 'bg-green-100 text-green-900 border border-green-200'
                          : 'bg-gray-100 text-gray-900'
                    }`}
                  >
                    {msg.role === 'human_agent' && (
                      <span className="text-xs font-medium text-green-600 block mb-1">人工客服</span>
                    )}
                    {msg.role === 'assistant' && (
                      <span className="text-xs font-medium text-gray-500 block mb-1">AI</span>
                    )}
                    <p className="whitespace-pre-wrap break-words">{msg.content}</p>
                    <span className="text-xs opacity-60 mt-1 block">
                      {new Date(msg.createdAt).toLocaleTimeString('zh-CN')}
                    </span>
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            {activeHitlSession.status === 'active' && (
              <div className="p-4 border-t border-gray-200">
                <div className="flex gap-2">
                  <textarea
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="输入消息…（Enter 发送，Shift+Enter 换行）"
                    className="flex-1 resize-none rounded border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    rows={2}
                    disabled={isSending}
                    aria-label="消息输入框"
                  />
                  <button
                    onClick={handleSend}
                    disabled={!inputText.trim() || isSending}
                    className="px-4 py-2 bg-blue-500 text-white text-sm rounded hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors self-end"
                    aria-label="发送消息"
                  >
                    {isSending ? '发送中…' : '发送'}
                  </button>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">
            选择一个会话开始处理
          </div>
        )}
      </div>
    </div>
  );
}
