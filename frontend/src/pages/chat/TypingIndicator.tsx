import { useEffect, useRef, useState } from 'react';
import { useChatStore } from '@/stores/chatStore';

// ── Props ──────────────────────────────────────────────────────

export interface TypingIndicatorProps {
  content: string;
}

// ── Animated dots (shown when no content yet) ──────────────────

function AnimatedDots() {
  return (
    <span className="inline-flex items-center gap-1" aria-label="正在输入">
      <span className="h-1.5 w-1.5 rounded-full bg-gray-400 animate-bounce [animation-delay:0ms]" />
      <span className="h-1.5 w-1.5 rounded-full bg-gray-400 animate-bounce [animation-delay:150ms]" />
      <span className="h-1.5 w-1.5 rounded-full bg-gray-400 animate-bounce [animation-delay:300ms]" />
    </span>
  );
}

// ── Main component ─────────────────────────────────────────────

export default function TypingIndicator({ content }: TypingIndicatorProps) {
  const setError = useChatStore((s) => s.setError);
  const [rendered, setRendered] = useState('');
  const rafRef = useRef<number>(0);
  const pendingRef = useRef('');

  useEffect(() => {
    // Accumulate new tokens that haven't been rendered yet
    if (content.length > rendered.length) {
      pendingRef.current = content;

      // Only schedule a new rAF if one isn't already pending
      if (rafRef.current === 0) {
        rafRef.current = requestAnimationFrame(() => {
          try {
            setRendered(pendingRef.current);
          } catch (err) {
            setError(
              err instanceof Error ? err.message : '渲染流式内容时发生错误',
            );
          } finally {
            rafRef.current = 0;
          }
        });
      }
    }
  }, [content, rendered, setError]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (rafRef.current !== 0) {
        cancelAnimationFrame(rafRef.current);
      }
    };
  }, []);

  // No content yet → show animated dots
  if (!content) {
    return <AnimatedDots />;
  }

  return (
    <span className="whitespace-pre-wrap">
      {rendered}
      <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-current" aria-hidden="true" />
    </span>
  );
}
