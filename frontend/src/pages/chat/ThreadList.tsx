import { useCallback } from 'react';
import { useSessionStore } from '@/stores/sessionStore';
import { useChatStore } from '@/stores/chatStore';

/**
 * ThreadList — 会话列表侧边栏
 *
 * Displays historical threads with title, last message time, and message count.
 * Supports creating new threads and switching between them.
 *
 * Requirements: 3.1, 3.2, 3.3
 */
export default function ThreadList() {
  const threads = useSessionStore((s) => s.threads);
  const activeThreadId = useSessionStore((s) => s.activeThreadId);
  const createThread = useSessionStore((s) => s.createThread);
  const switchThread = useSessionStore((s) => s.switchThread);
  const loadThread = useChatStore((s) => s.loadThread);

  const handleCreate = useCallback(() => {
    createThread();
  }, [createThread]);

  const handleSwitch = useCallback(
    (threadId: string) => {
      switchThread(threadId);
      loadThread(threadId);
    },
    [switchThread, loadThread],
  );

  return (
    <div className="flex h-full flex-col">
      {/* New thread button */}
      <button
        type="button"
        onClick={handleCreate}
        className="m-2 rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        aria-label="新建会话"
      >
        新建会话
      </button>

      {/* Thread list */}
      <nav className="flex-1 overflow-y-auto" aria-label="会话列表">
        {threads.length === 0 && (
          <p className="px-3 py-4 text-center text-xs text-gray-400">
            暂无会话
          </p>
        )}

        <ul role="list" className="space-y-0.5 px-1">
          {threads.map((thread) => {
            const isActive = thread.id === activeThreadId;
            return (
              <li key={thread.id}>
                <button
                  type="button"
                  onClick={() => handleSwitch(thread.id)}
                  className={`w-full rounded-md px-3 py-2 text-left text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 ${
                    isActive
                      ? 'bg-indigo-50 text-indigo-700 font-medium'
                      : 'text-gray-700 hover:bg-gray-100'
                  }`}
                  aria-current={isActive ? 'true' : undefined}
                  aria-label={`会话: ${thread.title || '新会话'}`}
                >
                  {/* Title */}
                  <span className="block truncate">
                    {thread.title || '新会话'}
                  </span>

                  {/* Meta: time + count */}
                  <span className="mt-0.5 flex items-center justify-between text-xs text-gray-400">
                    <time dateTime={thread.lastMessageAt}>
                      {formatTime(thread.lastMessageAt)}
                    </time>
                    <span>{thread.messageCount} 条</span>
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      </nav>
    </div>
  );
}

/** Format ISO timestamp to a short readable string. */
function formatTime(iso: string): string {
  try {
    const date = new Date(iso);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMin = Math.floor(diffMs / 60_000);

    if (diffMin < 1) return '刚刚';
    if (diffMin < 60) return `${diffMin} 分钟前`;

    const diffHour = Math.floor(diffMin / 60);
    if (diffHour < 24) return `${diffHour} 小时前`;

    // Same year → MM-DD, otherwise YYYY-MM-DD
    const sameYear = date.getFullYear() === now.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return sameYear
      ? `${month}-${day}`
      : `${date.getFullYear()}-${month}-${day}`;
  } catch {
    return '';
  }
}
