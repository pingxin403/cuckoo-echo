import { useRef, useEffect } from 'react';
import apiClient from '@/network/axios';
import { showToast } from '@/components/Toast';

export interface FeedbackPanelProps {
  threadId: string;
  messageId: string;
  onClose: () => void;
}

export default function FeedbackPanel({
  threadId,
  messageId,
  onClose,
}: FeedbackPanelProps) {
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        onClose();
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [onClose]);

  async function handleFeedback(type: 'thumbs_up' | 'thumbs_down') {
    try {
      await apiClient.post('/v1/feedback', {
        thread_id: threadId,
        message_id: messageId,
        feedback_type: type,
      });
      showToast('success', type === 'thumbs_up' ? '已标记为有帮助' : '已标记为无帮助');
      onClose();
    } catch {
      showToast('error', '反馈提交失败，请稍后重试');
    }
  }

  return (
    <div
      ref={panelRef}
      className="absolute bottom-full left-0 z-10 mb-1 flex rounded-lg border border-gray-200 bg-white p-1 shadow-lg"
      role="dialog"
      aria-label="反馈"
    >
      <button
        type="button"
        onClick={() => handleFeedback('thumbs_up')}
        className="rounded p-2 text-lg transition-colors hover:bg-green-50"
        aria-label="有帮助"
      >
        👍
      </button>
      <button
        type="button"
        onClick={() => handleFeedback('thumbs_down')}
        className="rounded p-2 text-lg transition-colors hover:bg-red-50"
        aria-label="无帮助"
      >
        👎
      </button>
    </div>
  );
}
