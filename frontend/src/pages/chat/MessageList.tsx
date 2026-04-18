import { useCallback, useEffect, useState } from 'react';
import { Virtuoso } from 'react-virtuoso';
import type { Message } from '@/types';
import { useChatStore } from '@/stores/chatStore';
import { useVirtualScroll } from '@/hooks/useVirtualScroll';

export interface MessageListProps {
  onLoadMore?: () => void;
}

/**
 * MessageList — 基于 react-virtuoso 的虚拟滚动消息列表
 *
 * - 动态高度测量（Virtuoso 自动处理）
 * - 新消息到达时自动滚动到底部（用户在底部时）
 * - 用户浏览历史时展示"有新消息"浮动按钮
 * - 向上滚动触发 onLoadMore 加载更早消息
 */
export default function MessageList({ onLoadMore }: MessageListProps) {
  const messages = useChatStore((s) => s.messages);
  const isStreaming = useChatStore((s) => s.isStreaming);
  const streamingContent = useChatStore((s) => s.streamingContent);
  const { isAtBottom, scrollToBottom, virtuosoRef, virtuosoProps } =
    useVirtualScroll();

  // Track previous message count to detect new arrivals
  const [prevCount, setPrevCount] = useState(messages.length);
  const hasNewMessages = !isAtBottom && messages.length > prevCount;

  useEffect(() => {
    if (isAtBottom) {
      setPrevCount(messages.length);
    }
  }, [messages.length, isAtBottom]);

  // Called when user scrolls to the top region
  const handleStartReached = useCallback(() => {
    onLoadMore?.();
  }, [onLoadMore]);

  const handleNewMessageClick = useCallback(() => {
    scrollToBottom();
    setPrevCount(messages.length);
  }, [scrollToBottom, messages.length]);

  return (
    <div className="relative flex-1 bg-gray-50" aria-label="消息列表">
      {messages.length === 0 && !isStreaming ? (
        /* Empty state */
        <div className="flex h-full flex-col items-center justify-center text-gray-400">
          <svg className="mb-3 h-12 w-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          <p className="text-sm">发送消息开始对话</p>
        </div>
      ) : (
        <Virtuoso
          ref={virtuosoRef}
          data={messages}
          startReached={handleStartReached}
          followOutput={virtuosoProps.followOutput}
          atBottomStateChange={virtuosoProps.atBottomStateChange}
          itemContent={(_index: number, message: Message) => (
            <div
              key={message.id}
              className="px-4 py-1.5"
              data-message-id={message.id}
              data-role={message.role}
              data-testid="message-bubble"
            >
              <div
                className={`inline-block rounded-2xl px-4 py-2.5 text-sm leading-relaxed shadow-sm ${
                  message.role === 'user'
                    ? 'float-right bg-[var(--ce-primary-color,#4f46e5)] text-white'
                    : 'float-left bg-white text-gray-800 ring-1 ring-gray-200'
                }`}
                style={{ maxWidth: '75%' }}
              >
                {message.content}
              </div>
              <div className="clear-both" />
            </div>
          )}
          className="h-full"
        />
      )}

      {/* Streaming assistant response */}
      {isStreaming && streamingContent && (
        <div className="px-4 py-1.5">
          <div className="inline-block max-w-[75%] rounded-2xl bg-white px-4 py-2.5 text-sm leading-relaxed text-gray-800 shadow-sm ring-1 ring-gray-200">
            {streamingContent}
            <span className="ml-0.5 inline-block animate-pulse text-indigo-500">▌</span>
          </div>
        </div>
      )}

      {/* Thinking indicator */}
      {isStreaming && !streamingContent && (
        <div className="px-4 py-1.5">
          <div className="inline-flex items-center gap-1.5 rounded-2xl bg-white px-4 py-2.5 text-sm text-gray-400 shadow-sm ring-1 ring-gray-200">
            <span className="flex gap-1">
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-gray-400" style={{ animationDelay: '0ms' }} />
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-gray-400" style={{ animationDelay: '150ms' }} />
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-gray-400" style={{ animationDelay: '300ms' }} />
            </span>
            AI 正在思考
          </div>
        </div>
      )}

      {/* "有新消息" floating button */}
      {hasNewMessages && (
        <button
          type="button"
          onClick={handleNewMessageClick}
          className="absolute bottom-4 left-1/2 -translate-x-1/2 rounded-full bg-[var(--ce-primary-color,#4f46e5)] px-4 py-2 text-sm text-white shadow-lg transition-opacity hover:opacity-90"
          aria-label="有新消息，点击滚动到底部"
        >
          有新消息
        </button>
      )}
    </div>
  );
}
