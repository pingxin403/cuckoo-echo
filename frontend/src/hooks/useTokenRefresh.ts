import { useEffect } from 'react';
import { useAuthStore } from '@/stores/authStore';
import { refreshTokenWithMutex } from '@/lib/tokenRefresh';

const CHECK_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes

export function useTokenRefresh(): void {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  useEffect(() => {
    if (!isAuthenticated) return;

    const intervalId = setInterval(() => {
      const needsRefresh = useAuthStore.getState().checkTokenExpiry();
      if (needsRefresh) {
        void refreshTokenWithMutex();
      }
    }, CHECK_INTERVAL_MS);

    return () => {
      clearInterval(intervalId);
    };
  }, [isAuthenticated]);
}
