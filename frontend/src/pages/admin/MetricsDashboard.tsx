import { useEffect, useState, useCallback } from 'react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { useMetricsStore } from '@/stores/adminStore';
import { Skeleton } from '@/components/Skeleton';
import apiClient from '@/network/axios';

/* ── Types ── */

interface MissedQuery {
  query: string;
  count: number;
}

type Period = '1d' | '7d' | '30d';

const PERIOD_OPTIONS: { label: string; value: Period }[] = [
  { label: '最近 1 天', value: '1d' },
  { label: '最近 7 天', value: '7d' },
  { label: '最近 30 天', value: '30d' },
];

/* ── Helpers ── */

/** Generate placeholder daily data for charts based on period */
function generateDailyPlaceholder(period: Period) {
  const days = period === '1d' ? 1 : period === '7d' ? 7 : 30;
  const now = new Date();
  return Array.from({ length: days }, (_, i) => {
    const d = new Date(now);
    d.setDate(d.getDate() - (days - 1 - i));
    const label = `${d.getMonth() + 1}/${d.getDate()}`;
    return { date: label, tokens: 0, conversations: 0 };
  });
}

/* ── Component ── */

export default function MetricsDashboard() {
  const { metricsOverview, metricsPeriod, isLoading, fetchMetrics, setMetricsPeriod } =
    useMetricsStore();

  const [missedQueries, setMissedQueries] = useState<MissedQuery[]>([]);
  const [missedLoading, setMissedLoading] = useState(false);

  const loadMissedQueries = useCallback(async () => {
    setMissedLoading(true);
    try {
      const res = await apiClient.get<MissedQuery[]>('/admin/v1/metrics/missed-queries');
      setMissedQueries(res.data);
    } catch {
      // error handled by axios interceptor
    } finally {
      setMissedLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    fetchMetrics();
    loadMissedQueries();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handlePeriodChange = (p: Period) => {
    setMetricsPeriod(p);
    fetchMetrics(p);
  };

  const handleRefresh = () => {
    fetchMetrics();
    loadMissedQueries();
  };

  const overview = metricsOverview;
  const chartData = generateDailyPlaceholder(metricsPeriod);

  // Derive some display values
  const escalationCount = overview
    ? Math.round(overview.totalConversations * overview.humanEscalationRate)
    : 0;
  const escalationPct = overview
    ? (overview.humanEscalationRate * 100).toFixed(1)
    : '0.0';
  const thumbUpPct = overview?.thumbUpRate != null
    ? (overview.thumbUpRate * 100).toFixed(1)
    : '--';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">数据看板</h1>
        <button
          onClick={handleRefresh}
          disabled={isLoading}
          className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          aria-label="刷新数据"
        >
          {isLoading ? '刷新中…' : '刷新'}
        </button>
      </div>

      {/* Time range selector */}
      <div className="flex gap-2" role="group" aria-label="时间范围选择">
        {PERIOD_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => handlePeriodChange(opt.value)}
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              metricsPeriod === opt.value
                ? 'bg-indigo-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
            aria-pressed={metricsPeriod === opt.value}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* Overview metric cards */}
      {isLoading && !overview ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} variant="card" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <MetricCard label="总对话数" value={overview?.totalConversations ?? 0} />
          <MetricCard label="转人工次数" value={escalationCount} />
          <MetricCard label="转人工率" value={`${escalationPct}%`} />
        </div>
      )}

      {/* Token & satisfaction cards */}
      {isLoading && !overview ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} variant="card" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <MetricCard label="总 Token 数" value={overview?.totalTokensUsed ?? 0} />
          <MetricCard
            label="消息数量"
            value={overview?.totalConversations ?? 0}
            subtitle="(基于对话数)"
          />
          <MetricCard label="用户满意度 (👍)" value={`${thumbUpPct}%`} />
        </div>
      )}

      {/* Charts */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Line chart — Token consumption trend */}
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <h2 className="mb-3 text-sm font-medium text-gray-700">Token 消耗趋势</h2>
          {isLoading && !overview ? (
            <Skeleton variant="card" />
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="tokens"
                  stroke="#4f46e5"
                  strokeWidth={2}
                  dot={false}
                  name="Token 数"
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Bar chart — Conversation distribution */}
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <h2 className="mb-3 text-sm font-medium text-gray-700">对话数分布</h2>
          {isLoading && !overview ? (
            <Skeleton variant="card" />
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="conversations" fill="#6366f1" name="对话数" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Missed queries list */}
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-medium text-gray-700">高频未命中问题</h2>
        {missedLoading ? (
          <Skeleton variant="list" />
        ) : missedQueries.length === 0 ? (
          <p className="py-4 text-center text-sm text-gray-400">暂无数据</p>
        ) : (
          <ul className="divide-y divide-gray-100">
            {missedQueries.map((q, idx) => (
              <li key={idx} className="flex items-center justify-between py-2">
                <span className="text-sm text-gray-800">{q.query}</span>
                <span className="rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-600">
                  {q.count} 次
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

/* ── MetricCard sub-component ── */

function MetricCard({
  label,
  value,
  subtitle,
}: {
  label: string;
  value: string | number;
  subtitle?: string;
}) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <p className="text-sm text-gray-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-gray-900">{value}</p>
      {subtitle && <p className="mt-0.5 text-xs text-gray-400">{subtitle}</p>}
    </div>
  );
}
