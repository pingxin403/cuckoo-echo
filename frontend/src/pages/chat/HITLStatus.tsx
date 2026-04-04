import { useEffect, useRef, useState } from 'react';
import { useSessionStore } from '@/stores/sessionStore';
import type { SessionStatus } from '@/types';

const HITL_PENDING_TIMEOUT_MS = 60_000;

/**
 * HITLStatus — monitors session status and shows HITL-related banners.
 *
 * - hitl_active  → "已转接人工客服，请稍候"
 * - active (after hitl) → "已恢复 AI 客服"
 * - hitl_pending 60s timeout → "当前无客服在线，已为您创建工单"
 */
export default function HITLStatus() {
  const status = useSessionStore((s) => s.status);
  const prevStatusRef = useRef<SessionStatus>(status);
  const [banner, setBanner] = useState<string | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const prev = prevStatusRef.current;
    prevStatusRef.current = status;

    // Clear any pending timeout when status changes
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }

    if (status === 'hitl_active') {
      setBanner('已转接人工客服，请稍候');
    } else if (status === 'active' && (prev === 'hitl_active' || prev === 'hitl_pending')) {
      setBanner('已恢复 AI 客服');
      // Auto-dismiss after 5s
      timeoutRef.current = setTimeout(() => setBanner(null), 5000);
    } else if (status === 'hitl_pending') {
      setBanner(null);
      timeoutRef.current = setTimeout(() => {
        setBanner('当前无客服在线，已为您创建工单，将在工作时间内回复');
      }, HITL_PENDING_TIMEOUT_MS);
    } else {
      setBanner(null);
    }

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [status]);

  if (!banner) return null;

  const isWarning = banner.includes('工单');
  const isRestored = banner.includes('恢复');

  return (
    <div
      role="status"
      aria-live="polite"
      className={`mx-4 my-2 rounded-lg px-3 py-2 text-center text-xs font-medium ${
        isWarning
          ? 'bg-amber-50 text-amber-700'
          : isRestored
            ? 'bg-blue-50 text-blue-700'
            : 'bg-green-50 text-green-700'
      }`}
    >
      {banner}
    </div>
  );
}
