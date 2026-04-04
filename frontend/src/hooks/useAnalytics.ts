import { useEffect, useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import { analytics } from '@/lib/analytics';

interface UseAnalyticsReturn {
  track: (event: string, params?: Record<string, unknown>) => void;
}

export function useAnalytics(): UseAnalyticsReturn {
  const location = useLocation();

  // Auto-track page_view on route change
  useEffect(() => {
    analytics.track('page_view', {
      page_name: location.pathname,
      timestamp: new Date().toISOString(),
    });
  }, [location.pathname]);

  const track = useCallback(
    (event: string, params?: Record<string, unknown>) => {
      analytics.track(event, params);
    },
    [],
  );

  return { track };
}
