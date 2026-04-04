import { useState, useRef, useEffect } from 'react';
import apiClient from '@/network/axios';
import { showToast } from '@/components/Toast';

const FEEDBACK_REASONS = [
  '回答不准确',
  '没有回答我的问题',
  '回答太慢',
  '其他',
] as const;

type FeedbackReason = (typeof FEEDBACK_REASONS)[number];

export interface FeedbackPanelProps {
  threadId: string;
  messageId: string;
  onClose: () => void;
  onSubmitted: () => void;
}

export default function FeedbackPanel({
  threadId,
  messageId,
  onClose,
  onSubmitted,
}: FeedbackPanelProps) {
  const [selectedReason, setSelectedReason] = useState<FeedbackReason | null>(null);
  const [customText, setCustomText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        onClose();
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [onClose]);

  async function handleSubmit() {
    if (!selectedReason) return;
    const reason =
      selectedReason === '其他' ? customText.trim() || '其他' : selectedReason;

    setSubmitting(true);
    try {
      await apiClient.post('/v1/feedback', {
        thread_id: threadId,
        message_id: messageId,
        rating: 'down',
        reason,
      });
      showToast('success', '感谢您的反馈');
      onSubmitted();
    } catch {
      showToast('error', '反馈提交失败，请稍后重试');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      ref={panelRef}
      className="absolute bottom-full left-0 z-10 mb-1 w-56 rounded-lg border border-gray-200 bg-white p-2 shadow-lg"
      role="dialog"
      aria-label="反馈原因"
    >
      <p className="mb-1.5 text-xs font-medium text-gray-700">请选择原因：</p>
      <ul className="flex flex-col gap-1">
        {FEEDBACK_REASONS.map((reason) => (
          <li key={reason}>
            <button
              type="button"
              onClick={() => setSelectedReason(reason)}
              className={`w-full rounded px-2 py-1 text-left text-xs transition-colors ${
                selectedReason === reason
                  ? 'bg-red-50 text-red-700'
                  : 'text-gray-600 hover:bg-gray-50'
              }`}
            >
              {reason}
            </button>
          </li>
        ))}
      </ul>

      {selectedReason === '其他' && (
        <textarea
          value={customText}
          onChange={(e) => setCustomText(e.target.value)}
          placeholder="请描述您的问题…"
          className="mt-1.5 w-full resize-none rounded border border-gray-200 p-1.5 text-xs text-gray-700 outline-none focus:border-gray-400"
          rows={2}
          maxLength={200}
          aria-label="自由文本反馈"
        />
      )}

      <button
        type="button"
        disabled={!selectedReason || submitting}
        onClick={handleSubmit}
        className="mt-1.5 w-full rounded bg-red-500 px-2 py-1 text-xs text-white transition-colors hover:bg-red-600 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {submitting ? '提交中…' : '提交反馈'}
      </button>
    </div>
  );
}
