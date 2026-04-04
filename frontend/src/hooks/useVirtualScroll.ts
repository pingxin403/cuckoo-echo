import { useCallback, useRef, useState } from 'react';
import type { VirtuosoHandle } from 'react-virtuoso';

interface UseVirtualScrollReturn {
  isAtBottom: boolean;
  scrollToBottom: () => void;
  virtuosoRef: React.RefObject<VirtuosoHandle | null>;
  virtuosoProps: {
    followOutput: 'smooth' | false;
    atBottomStateChange: (atBottom: boolean) => void;
  };
}

export function useVirtualScroll(): UseVirtualScrollReturn {
  const [isAtBottom, setIsAtBottom] = useState(true);
  const virtuosoRef = useRef<VirtuosoHandle | null>(null);

  const atBottomStateChange = useCallback((atBottom: boolean) => {
    setIsAtBottom(atBottom);
  }, []);

  const scrollToBottom = useCallback(() => {
    virtuosoRef.current?.scrollToIndex({
      index: 'LAST',
      behavior: 'smooth',
    });
  }, []);

  return {
    isAtBottom,
    scrollToBottom,
    virtuosoRef,
    virtuosoProps: {
      followOutput: isAtBottom ? 'smooth' : false,
      atBottomStateChange,
    },
  };
}
