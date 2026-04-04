import { useCallback, useEffect, useRef } from 'react';
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
  const { isAtBottom, scrollToBottom, virtuosoRef, virtuosoProps } =
    useVirtualScroll();

  // Track previous message count to detect new arrivals
  const prevCountRef = useRef(messages.length);
  const hasNewMessages = !isAtBottom && messages.length > prevCountRef.current;

  useEffect(() => {
    if (isAtBottom) {
      prevCountRef.current = messages.length;
    }
  }, [messages.length, isAtBottom]);

  // Called when user scrolls to the top region
  const handleStartReached = useCallback(() => {
    onLoadMore?.();
  }, [onLoadMore]);

  const handleNewMessageClick = useCallback(() => {
    scrollToBottom();
    prevCountRef.current = messages.length;
  }, [scrollToBottom, messages.length]);

  return (
    <div className="relative flex-1" aria-label="消息列表">
      <Virtuoso
        ref={virtuosoRef}
        data={messages}
        startReached={handleStartReached}
        followOutput={virtuosoProps.followOutput}
        atBottomStateChange={virtuosoProps.atBottomStateChange}
        itemContent={(_index: number, message: Message) => (
          <div
            key={message.id}
            className="px-4 py-2"
            data-message-id={message.id}
            data-role={message.role}
          >
            {/* Placeholder — MessageBubble will replace this in task 9.3 */}
            <div
              className={`rounded-lg px-3 py-2 text-sm max-w-[80%] ${
                message.role === 'user'
                  ? 'ml-auto bg-[var(--ce-primary-color,#4f46e5)] text-white'
                  : 'mr-auto bg-gray-100 text-gray-900'
              }`}
            >
              {message.content}
            </div>
          </div>
        )}
        className="h-full"
      />

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
