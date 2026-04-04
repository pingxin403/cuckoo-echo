import { describe, it, expect, beforeAll, afterAll, afterEach, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { server } from '@/mocks/server';
import { useMetricsStore } from '@/stores/adminStore';

// Mock recharts — return simple divs to avoid jsdom measurement issues
vi.mock('recharts', () => ({
  LineChart: ({ children }: { children: React.ReactNode }) => <div data-testid="line-chart">{children}</div>,
  BarChart: ({ children }: { children: React.ReactNode }) => <div data-testid="bar-chart">{children}</div>,
  Line: () => <div data-testid="line" />,
  Bar: () => <div data-testid="bar" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
}));

// Lazy import after mock is set up
const { default: MetricsDashboard } = await import('@/pages/admin/MetricsDashboard');

beforeAll(() => server.listen({ onUnhandledRequest: 'bypass' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

beforeEach(() => {
  useMetricsStore.setState({
    metricsOverview: null,
    metricsPeriod: '7d',
    isLoading: false,
  });
});

function renderDashboard() {
  return render(
    <BrowserRouter>
      <MetricsDashboard />
    </BrowserRouter>,
  );
}

describe('MetricsDashboard', () => {
  it('renders "数据看板" heading', () => {
    renderDashboard();
    expect(screen.getByText('数据看板')).toBeInTheDocument();
  });

  it('renders time range selector buttons (1d, 7d, 30d)', () => {
    renderDashboard();
    expect(screen.getByText('最近 1 天')).toBeInTheDocument();
    expect(screen.getByText('最近 7 天')).toBeInTheDocument();
    expect(screen.getByText('最近 30 天')).toBeInTheDocument();
  });

  it('renders refresh button', () => {
    renderDashboard();
    expect(screen.getByRole('button', { name: '刷新数据' })).toBeInTheDocument();
  });
});
