import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet, useSearchParams } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { useAnalytics } from '@/hooks/useAnalytics';
import { ToastProvider } from '@/components/Toast';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { OfflineBanner } from '@/components/OfflineBanner';
import { Skeleton } from '@/components/Skeleton';
import LoginPage from '@/pages/LoginPage';
import DashboardLayout from '@/pages/admin/DashboardLayout';
import ChatWidget from '@/pages/chat/ChatWidget';

// Lazy-loaded admin pages for code splitting
const MetricsDashboard = lazy(() => import('@/pages/admin/MetricsDashboard'));
const KnowledgeManager = lazy(() => import('@/pages/admin/KnowledgeManager'));
const HITLPanel = lazy(() => import('@/pages/admin/HITLPanel'));
const ConfigPanel = lazy(() => import('@/pages/admin/ConfigPanel'));
const SandboxRunner = lazy(() => import('@/pages/admin/SandboxRunner'));

/**
 * ProtectedRoute — redirects unauthenticated users to /login.
 * Renders child routes via <Outlet /> when authenticated.
 */
function ProtectedRoute() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  return <Outlet />;
}

/**
 * AnalyticsProvider — calls useAnalytics() to auto-track page_view on route changes.
 * Must be rendered inside <BrowserRouter>.
 */
function AnalyticsProvider({ children }: { children: React.ReactNode }) {
  useAnalytics();
  return <>{children}</>;
}

/**
 * ChatPage — reads apiKey from URL search params and renders ChatWidget.
 * Usage: /chat?api_key=ck_xxx&theme=light&lang=zh-CN
 */
function ChatPage() {
  const [searchParams] = useSearchParams();
  const apiKey = searchParams.get('api_key') ?? '';
  const theme = (searchParams.get('theme') as 'light' | 'dark') || undefined;
  const position = (searchParams.get('position') as 'bottom-right' | 'bottom-left') || undefined;
  const lang = (searchParams.get('lang') as 'zh-CN' | 'en') || undefined;
  const primaryColor = searchParams.get('primary_color') ?? undefined;
  const bgColor = searchParams.get('bg_color') ?? undefined;
  const logoUrl = searchParams.get('logo_url') ?? undefined;

  return (
    <ChatWidget
      apiKey={apiKey}
      theme={theme}
      position={position}
      lang={lang}
      primaryColor={primaryColor}
      bgColor={bgColor}
      logoUrl={logoUrl}
    />
  );
}

/* ── Root App component ── */

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <ToastProvider>
          <AnalyticsProvider>
            <OfflineBanner />
            <Routes>
              {/* Public routes */}
              <Route path="/login" element={<LoginPage />} />
              <Route path="/chat" element={<ChatPage />} />

              {/* Protected admin routes */}
              <Route path="/admin" element={<ProtectedRoute />}>
                <Route element={<DashboardLayout />}>
                  <Route index element={<Navigate to="/admin/metrics" replace />} />
                  <Route path="metrics" element={<Suspense fallback={<Skeleton />}><MetricsDashboard /></Suspense>} />
                  <Route path="knowledge" element={<Suspense fallback={<Skeleton />}><KnowledgeManager /></Suspense>} />
                  <Route path="hitl" element={<Suspense fallback={<Skeleton />}><HITLPanel /></Suspense>} />
                  <Route path="config" element={<Suspense fallback={<Skeleton />}><ConfigPanel /></Suspense>} />
                  <Route path="sandbox" element={<Suspense fallback={<Skeleton />}><SandboxRunner /></Suspense>} />
                </Route>
              </Route>

              {/* Catch-all → login */}
              <Route path="*" element={<Navigate to="/login" replace />} />
            </Routes>
          </AnalyticsProvider>
        </ToastProvider>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
