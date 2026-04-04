import { useState, useCallback, useEffect } from 'react';
import { useSandboxStore } from '@/stores/adminStore';
import { useToast } from '@/components/Toast';
import type { TestCase, SandboxResult } from '@/types';

// ─── localStorage helpers ──────────────────────────────────────

interface SavedTestCaseSet {
  name: string;
  testCases: TestCase[];
  savedAt: number;
}

const STORAGE_KEY = 'cuckoo_sandbox_sets';
const MAX_SAVED = 10;

function loadSavedSets(): SavedTestCaseSet[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as SavedTestCaseSet[]) : [];
  } catch {
    return [];
  }
}

function persistSets(sets: SavedTestCaseSet[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(sets.slice(0, MAX_SAVED)));
}

// ─── Metric helpers ────────────────────────────────────────────

const METRIC_LABELS: Record<string, string> = {
  faithfulness: 'Faithfulness',
  contextPrecision: 'Context Precision',
  contextRecall: 'Context Recall',
  answerRelevancy: 'Answer Relevancy',
};

const METRIC_KEYS = Object.keys(METRIC_LABELS) as (keyof SandboxResult['scores'])[];

function scoreColor(score: number, threshold: number): string {
  return score >= threshold ? 'text-green-600' : 'text-red-600 font-semibold';
}

function scoreBg(score: number, threshold: number): string {
  return score >= threshold ? 'bg-green-50' : 'bg-red-50';
}

// ─── Empty test case factory ───────────────────────────────────

function emptyCase(): TestCase {
  return { query: '', reference: '', contexts: [''] };
}

// ─── Component ─────────────────────────────────────────────────

export default function SandboxRunner() {
  const { sandboxResults, isRunning, runSandbox, clearResults } = useSandboxStore();
  const { showToast } = useToast();

  const [testCases, setTestCases] = useState<TestCase[]>([emptyCase()]);
  const [previousResults, setPreviousResults] = useState<SandboxResult[] | null>(null);
  const [showComparison, setShowComparison] = useState(false);

  // saved sets
  const [savedSets, setSavedSets] = useState<SavedTestCaseSet[]>(loadSavedSets);
  const [saveName, setSaveName] = useState('');
  const [loadMenuOpen, setLoadMenuOpen] = useState(false);

  // snapshot previous results before a new run
  const handleRun = useCallback(async () => {
    const valid = testCases.some((tc) => tc.query.trim());
    if (!valid) {
      showToast('error', '请至少填写一个查询');
      return;
    }
    // store current results as "previous" for comparison
    if (sandboxResults.length > 0) {
      setPreviousResults(sandboxResults);
    }
    try {
      await runSandbox(testCases.filter((tc) => tc.query.trim()));
    } catch {
      showToast('error', '运行测试失败');
    }
  }, [testCases, sandboxResults, runSandbox, showToast]);

  // ─── Test case CRUD ──────────────────────────────────────────

  const updateCase = useCallback((idx: number, patch: Partial<TestCase>) => {
    setTestCases((prev) => prev.map((tc, i) => (i === idx ? { ...tc, ...patch } : tc)));
  }, []);

  const addCase = useCallback(() => setTestCases((prev) => [...prev, emptyCase()]), []);

  const removeCase = useCallback(
    (idx: number) => setTestCases((prev) => (prev.length <= 1 ? prev : prev.filter((_, i) => i !== idx))),
    [],
  );

  const addContext = useCallback((caseIdx: number) => {
    setTestCases((prev) =>
      prev.map((tc, i) => (i === caseIdx ? { ...tc, contexts: [...tc.contexts, ''] } : tc)),
    );
  }, []);

  const updateContext = useCallback((caseIdx: number, ctxIdx: number, value: string) => {
    setTestCases((prev) =>
      prev.map((tc, i) =>
        i === caseIdx
          ? { ...tc, contexts: tc.contexts.map((c, j) => (j === ctxIdx ? value : c)) }
          : tc,
      ),
    );
  }, []);

  const removeContext = useCallback((caseIdx: number, ctxIdx: number) => {
    setTestCases((prev) =>
      prev.map((tc, i) =>
        i === caseIdx
          ? { ...tc, contexts: tc.contexts.length <= 1 ? tc.contexts : tc.contexts.filter((_, j) => j !== ctxIdx) }
          : tc,
      ),
    );
  }, []);

  // ─── Save / Load ────────────────────────────────────────────

  const handleSave = useCallback(() => {
    const name = saveName.trim();
    if (!name) {
      showToast('error', '请输入用例集名称');
      return;
    }
    const newSet: SavedTestCaseSet = { name, testCases, savedAt: Date.now() };
    const updated = [newSet, ...savedSets.filter((s) => s.name !== name)].slice(0, MAX_SAVED);
    setSavedSets(updated);
    persistSets(updated);
    setSaveName('');
    showToast('success', `已保存「${name}」`);
  }, [saveName, testCases, savedSets, showToast]);

  const handleLoad = useCallback(
    (set: SavedTestCaseSet) => {
      setTestCases(set.testCases.length > 0 ? set.testCases : [emptyCase()]);
      setLoadMenuOpen(false);
      showToast('info', `已加载「${set.name}」`);
    },
    [showToast],
  );

  const handleDeleteSet = useCallback(
    (name: string) => {
      const updated = savedSets.filter((s) => s.name !== name);
      setSavedSets(updated);
      persistSets(updated);
    },
    [savedSets],
  );

  // close load menu on outside click
  useEffect(() => {
    if (!loadMenuOpen) return;
    const handler = () => setLoadMenuOpen(false);
    document.addEventListener('click', handler, { once: true });
    return () => document.removeEventListener('click', handler);
  }, [loadMenuOpen]);

  // ─── Styles ──────────────────────────────────────────────────

  const sectionClass = 'rounded-lg border border-gray-200 bg-white p-6';
  const labelClass = 'block text-sm font-medium text-gray-700 mb-1';
  const inputClass =
    'w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500';
  const btnPrimary =
    'rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1';
  const btnSecondary =
    'rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1';

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-gray-900">沙盒测试</h1>

      {/* ── Save / Load bar ── */}
      <div className="flex flex-wrap items-center gap-3">
        <input
          type="text"
          className={`${inputClass} max-w-[200px]`}
          placeholder="用例集名称"
          value={saveName}
          onChange={(e) => setSaveName(e.target.value)}
          aria-label="用例集名称"
        />
        <button className={btnSecondary} onClick={handleSave} aria-label="保存用例集">
          保存
        </button>
        <div className="relative">
          <button
            className={btnSecondary}
            onClick={(e) => {
              e.stopPropagation();
              setLoadMenuOpen((v) => !v);
            }}
            aria-label="加载用例集"
          >
            加载 ▾
          </button>
          {loadMenuOpen && savedSets.length > 0 && (
            <div className="absolute left-0 top-full z-10 mt-1 w-56 rounded-md border border-gray-200 bg-white shadow-lg">
              {savedSets.map((s) => (
                <div key={s.name} className="flex items-center justify-between px-3 py-2 hover:bg-gray-50">
                  <button
                    className="flex-1 text-left text-sm text-gray-700"
                    onClick={() => handleLoad(s)}
                  >
                    {s.name}
                  </button>
                  <button
                    className="ml-2 text-xs text-red-500 hover:text-red-700"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteSet(s.name);
                    }}
                    aria-label={`删除用例集 ${s.name}`}
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          )}
          {loadMenuOpen && savedSets.length === 0 && (
            <div className="absolute left-0 top-full z-10 mt-1 w-56 rounded-md border border-gray-200 bg-white p-3 text-sm text-gray-500 shadow-lg">
              暂无保存的用例集
            </div>
          )}
        </div>
      </div>

      {/* ── Test cases input ── */}
      <section className={sectionClass} aria-label="测试用例">
        <h2 className="mb-4 text-lg font-medium text-gray-800">测试用例</h2>
        <div className="space-y-6">
          {testCases.map((tc, caseIdx) => (
            <div key={caseIdx} className="rounded-md border border-gray-100 bg-gray-50 p-4">
              <div className="mb-3 flex items-center justify-between">
                <span className="text-sm font-medium text-gray-600">用例 #{caseIdx + 1}</span>
                {testCases.length > 1 && (
                  <button
                    className="text-xs text-red-500 hover:text-red-700"
                    onClick={() => removeCase(caseIdx)}
                    aria-label={`删除用例 ${caseIdx + 1}`}
                  >
                    删除
                  </button>
                )}
              </div>
              <div className="space-y-3">
                <div>
                  <label className={labelClass}>查询 (Query)</label>
                  <input
                    type="text"
                    className={inputClass}
                    value={tc.query}
                    onChange={(e) => updateCase(caseIdx, { query: e.target.value })}
                    placeholder="输入测试查询…"
                    aria-label={`用例 ${caseIdx + 1} 查询`}
                  />
                </div>
                <div>
                  <label className={labelClass}>参考答案 (Reference)</label>
                  <textarea
                    rows={2}
                    className={inputClass}
                    value={tc.reference}
                    onChange={(e) => updateCase(caseIdx, { reference: e.target.value })}
                    placeholder="输入参考答案…"
                    aria-label={`用例 ${caseIdx + 1} 参考答案`}
                  />
                </div>
                <div>
                  <div className="mb-1 flex items-center justify-between">
                    <label className="text-sm font-medium text-gray-700">上下文 (Contexts)</label>
                    <button
                      className="text-xs text-blue-600 hover:text-blue-800"
                      onClick={() => addContext(caseIdx)}
                      aria-label={`用例 ${caseIdx + 1} 添加上下文`}
                    >
                      + 添加
                    </button>
                  </div>
                  {tc.contexts.map((ctx, ctxIdx) => (
                    <div key={ctxIdx} className="mb-2 flex items-start gap-2">
                      <textarea
                        rows={2}
                        className={`${inputClass} flex-1`}
                        value={ctx}
                        onChange={(e) => updateContext(caseIdx, ctxIdx, e.target.value)}
                        placeholder={`上下文 ${ctxIdx + 1}`}
                        aria-label={`用例 ${caseIdx + 1} 上下文 ${ctxIdx + 1}`}
                      />
                      {tc.contexts.length > 1 && (
                        <button
                          className="mt-1 text-xs text-red-500 hover:text-red-700"
                          onClick={() => removeContext(caseIdx, ctxIdx)}
                          aria-label={`删除上下文 ${ctxIdx + 1}`}
                        >
                          ✕
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
        <div className="mt-4 flex items-center gap-3">
          <button className={btnSecondary} onClick={addCase} aria-label="添加测试用例">
            + 添加用例
          </button>
        </div>
      </section>

      {/* ── Run button ── */}
      <div className="flex items-center gap-3">
        <button className={btnPrimary} disabled={isRunning} onClick={handleRun} aria-label="运行测试">
          {isRunning ? '运行中…' : '运行测试'}
        </button>
        {sandboxResults.length > 0 && (
          <button
            className={btnSecondary}
            onClick={() => {
              clearResults();
              setPreviousResults(null);
              setShowComparison(false);
            }}
            aria-label="清除结果"
          >
            清除结果
          </button>
        )}
        {previousResults && sandboxResults.length > 0 && (
          <button
            className={btnSecondary}
            onClick={() => setShowComparison((v) => !v)}
            aria-label="切换对比视图"
          >
            {showComparison ? '隐藏对比' : '对比视图'}
          </button>
        )}
      </div>

      {/* ── Results ── */}
      {sandboxResults.length > 0 && !showComparison && (
        <section className={sectionClass} aria-label="测试结果">
          <h2 className="mb-4 text-lg font-medium text-gray-800">测试结果</h2>
          <div className="space-y-4">
            {sandboxResults.map((result, idx) => (
              <ResultCard key={idx} result={result} index={idx} />
            ))}
          </div>
        </section>
      )}

      {/* ── Comparison view ── */}
      {showComparison && previousResults && sandboxResults.length > 0 && (
        <section className={sectionClass} aria-label="对比视图">
          <h2 className="mb-4 text-lg font-medium text-gray-800">对比视图</h2>
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <div>
              <h3 className="mb-3 text-sm font-medium text-gray-500">旧结果</h3>
              <div className="space-y-4">
                {previousResults.map((result, idx) => (
                  <ResultCard key={idx} result={result} index={idx} />
                ))}
              </div>
            </div>
            <div>
              <h3 className="mb-3 text-sm font-medium text-gray-500">新结果</h3>
              <div className="space-y-4">
                {sandboxResults.map((result, idx) => (
                  <ResultCard key={idx} result={result} index={idx} />
                ))}
              </div>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}

// ─── Result card sub-component ─────────────────────────────────

function ResultCard({ result, index }: { result: SandboxResult; index: number }) {
  return (
    <div
      className={`rounded-md border p-4 ${result.passed ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}`}
    >
      <div className="mb-2 flex items-center justify-between">
        <span className="text-sm font-medium text-gray-700">用例 #{index + 1}</span>
        <span
          className={`rounded-full px-2 py-0.5 text-xs font-medium ${result.passed ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}
        >
          {result.passed ? '通过' : '未通过'}
        </span>
      </div>
      <p className="mb-3 text-xs text-gray-500 truncate" title={result.testCase.query}>
        {result.testCase.query}
      </p>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {METRIC_KEYS.map((key) => {
          const score = result.scores[key];
          const threshold = result.thresholds[key] ?? 0;
          return (
            <div key={key} className={`rounded-md p-2 text-center ${scoreBg(score, threshold)}`}>
              <div className="text-xs text-gray-500">{METRIC_LABELS[key]}</div>
              <div className={`text-lg font-semibold ${scoreColor(score, threshold)}`}>
                {(score * 100).toFixed(1)}%
              </div>
              <div className="text-xs text-gray-400">阈值 {(threshold * 100).toFixed(0)}%</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
