import { useEffect, useState, useCallback } from 'react';
import { useConfigStore } from '@/stores/adminStore';
import { useToast } from '@/components/Toast';
import { ConfirmDialog } from '@/components/ConfirmDialog';
import { analytics } from '@/lib/analytics';
import apiClient from '@/network/axios';
import type { PersonaConfig, ModelConfig, RateLimitConfig } from '@/types';

const MODEL_OPTIONS = [
  'gpt-4o',
  'gpt-4o-mini',
  'gpt-4-turbo',
  'gpt-3.5-turbo',
  'claude-3-opus',
  'claude-3-sonnet',
  'claude-3-haiku',
  'deepseek-chat',
  'qwen-max',
  'qwen-plus',
];

export default function ConfigPanel() {
  const { persona, modelConfig, rateLimitConfig, fetchConfig, savePersona, saveModelConfig, saveRateLimitConfig } =
    useConfigStore();
  const { showToast } = useToast();

  // ─── Local form state ────────────────────────────────────────
  const [personaForm, setPersonaForm] = useState<PersonaConfig>({
    systemPrompt: '',
    personaName: '',
    greeting: '',
  });
  const [modelForm, setModelForm] = useState<ModelConfig>({
    primaryModel: MODEL_OPTIONS[0],
    fallbackModel: MODEL_OPTIONS[1],
    temperature: 0.7,
  });
  const [rateForm, setRateForm] = useState<RateLimitConfig>({
    tenantRps: 100,
    userRps: 10,
  });
  const [saving, setSaving] = useState<string | null>(null);
  const [clearDialogOpen, setClearDialogOpen] = useState(false);
  const [clearing, setClearing] = useState(false);

  // ─── Embed code generator state ──────────────────────────────
  const [embedTheme, setEmbedTheme] = useState<'light' | 'dark'>('light');
  const [embedPosition, setEmbedPosition] = useState<'bottom-right' | 'bottom-left'>('bottom-right');
  const [embedLang, setEmbedLang] = useState<'zh-CN' | 'en'>('zh-CN');
  const [embedApiKey, setEmbedApiKey] = useState('ck_your_api_key');
  const [copied, setCopied] = useState(false);

  // ─── Load config on mount ────────────────────────────────────
  useEffect(() => {
    fetchConfig().catch(() => {
      showToast('error', '加载配置失败');
    });
  }, [fetchConfig, showToast]);

  // Prefill forms when store data arrives
  useEffect(() => {
    if (persona) setPersonaForm(persona);
  }, [persona]);
  useEffect(() => {
    if (modelConfig) setModelForm(modelConfig);
  }, [modelConfig]);
  useEffect(() => {
    if (rateLimitConfig) setRateForm(rateLimitConfig);
  }, [rateLimitConfig]);

  // ─── Save handlers ───────────────────────────────────────────
  const handleSavePersona = useCallback(async () => {
    setSaving('persona');
    try {
      await savePersona(personaForm);
      analytics.track('config_changed', { config_type: 'persona' });
      showToast('success', 'Persona 配置已保存');
    } catch {
      showToast('error', 'Persona 配置保存失败');
    } finally {
      setSaving(null);
    }
  }, [personaForm, savePersona, showToast]);

  const handleSaveModel = useCallback(async () => {
    setSaving('model');
    try {
      await saveModelConfig(modelForm);
      analytics.track('config_changed', { config_type: 'model' });
      showToast('success', '模型配置已保存');
    } catch {
      showToast('error', '模型配置保存失败');
    } finally {
      setSaving(null);
    }
  }, [modelForm, saveModelConfig, showToast]);

  const handleSaveRate = useCallback(async () => {
    setSaving('rate');
    try {
      await saveRateLimitConfig(rateForm);
      analytics.track('config_changed', { config_type: 'rate_limit' });
      showToast('success', '限流配置已保存');
    } catch {
      showToast('error', '限流配置保存失败');
    } finally {
      setSaving(null);
    }
  }, [rateForm, saveRateLimitConfig, showToast]);

  // ─── Clear cache ─────────────────────────────────────────────
  const handleClearCache = useCallback(async () => {
    setClearing(true);
    try {
      await apiClient.post('/admin/v1/cache/clear');
      showToast('success', '语义缓存已清除');
    } catch {
      showToast('error', '清除缓存失败');
    } finally {
      setClearing(false);
      setClearDialogOpen(false);
    }
  }, [showToast]);

  // ─── Embed snippet ──────────────────────────────────────────
  const embedSnippet = `<script src="${window.location.origin}/embed.js"
  data-api-key="${embedApiKey}"
  data-theme="${embedTheme}"
  data-position="${embedPosition}"
  data-lang="${embedLang}">
</script>`;

  const handleCopySnippet = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(embedSnippet);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      showToast('error', '复制失败');
    }
  }, [embedSnippet, showToast]);

  const sectionClass = 'rounded-lg border border-gray-200 bg-white p-6';
  const labelClass = 'block text-sm font-medium text-gray-700 mb-1';
  const inputClass = 'w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500';
  const btnPrimary = 'rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1';

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-gray-900">配置中心</h1>

      {/* ── Persona Config ── */}
      <section className={sectionClass} aria-label="Persona 配置">
        <h2 className="mb-4 text-lg font-medium text-gray-800">Persona 配置</h2>
        <div className="space-y-4">
          <div>
            <label htmlFor="systemPrompt" className={labelClass}>系统提示词</label>
            <textarea
              id="systemPrompt"
              rows={4}
              className={inputClass}
              value={personaForm.systemPrompt}
              onChange={(e) => setPersonaForm((f) => ({ ...f, systemPrompt: e.target.value }))}
              placeholder="输入系统提示词…"
            />
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="personaName" className={labelClass}>机器人名称</label>
              <input
                id="personaName"
                type="text"
                className={inputClass}
                value={personaForm.personaName}
                onChange={(e) => setPersonaForm((f) => ({ ...f, personaName: e.target.value }))}
                placeholder="例如：小布"
              />
            </div>
            <div>
              <label htmlFor="greeting" className={labelClass}>问候语</label>
              <input
                id="greeting"
                type="text"
                className={inputClass}
                value={personaForm.greeting}
                onChange={(e) => setPersonaForm((f) => ({ ...f, greeting: e.target.value }))}
                placeholder="例如：你好，有什么可以帮您？"
              />
            </div>
          </div>
          <div className="flex justify-end">
            <button className={btnPrimary} disabled={saving === 'persona'} onClick={handleSavePersona} aria-label="保存 Persona 配置">
              {saving === 'persona' ? '保存中…' : '保存'}
            </button>
          </div>
        </div>
      </section>

      {/* ── Model Config ── */}
      <section className={sectionClass} aria-label="模型配置">
        <h2 className="mb-4 text-lg font-medium text-gray-800">模型配置</h2>
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="primaryModel" className={labelClass}>主模型</label>
              <select
                id="primaryModel"
                className={inputClass}
                value={modelForm.primaryModel}
                onChange={(e) => setModelForm((f) => ({ ...f, primaryModel: e.target.value }))}
              >
                {MODEL_OPTIONS.map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="fallbackModel" className={labelClass}>备用模型</label>
              <select
                id="fallbackModel"
                className={inputClass}
                value={modelForm.fallbackModel}
                onChange={(e) => setModelForm((f) => ({ ...f, fallbackModel: e.target.value }))}
              >
                {MODEL_OPTIONS.map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <label htmlFor="temperature" className={labelClass}>
              温度 (Temperature): {modelForm.temperature.toFixed(1)}
            </label>
            <input
              id="temperature"
              type="range"
              min="0"
              max="1"
              step="0.1"
              className="w-full accent-blue-600"
              value={modelForm.temperature}
              onChange={(e) => setModelForm((f) => ({ ...f, temperature: parseFloat(e.target.value) }))}
            />
            <div className="mt-1 flex justify-between text-xs text-gray-400">
              <span>0.0 精确</span>
              <span>1.0 创意</span>
            </div>
          </div>
          <div className="flex justify-end">
            <button className={btnPrimary} disabled={saving === 'model'} onClick={handleSaveModel} aria-label="保存模型配置">
              {saving === 'model' ? '保存中…' : '保存'}
            </button>
          </div>
        </div>
      </section>

      {/* ── Rate Limit Config ── */}
      <section className={sectionClass} aria-label="限流配置">
        <h2 className="mb-4 text-lg font-medium text-gray-800">限流配置</h2>
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="tenantRps" className={labelClass}>租户级 RPS</label>
              <input
                id="tenantRps"
                type="number"
                min="1"
                className={inputClass}
                value={rateForm.tenantRps}
                onChange={(e) => setRateForm((f) => ({ ...f, tenantRps: parseInt(e.target.value, 10) || 0 }))}
              />
            </div>
            <div>
              <label htmlFor="userRps" className={labelClass}>用户级 RPS</label>
              <input
                id="userRps"
                type="number"
                min="1"
                className={inputClass}
                value={rateForm.userRps}
                onChange={(e) => setRateForm((f) => ({ ...f, userRps: parseInt(e.target.value, 10) || 0 }))}
              />
            </div>
          </div>
          <div className="flex justify-end">
            <button className={btnPrimary} disabled={saving === 'rate'} onClick={handleSaveRate} aria-label="保存限流配置">
              {saving === 'rate' ? '保存中…' : '保存'}
            </button>
          </div>
        </div>
      </section>

      {/* ── Clear Cache ── */}
      <section className={sectionClass} aria-label="缓存管理">
        <h2 className="mb-4 text-lg font-medium text-gray-800">缓存管理</h2>
        <p className="mb-4 text-sm text-gray-600">清除语义缓存后，后续请求将重新生成回答。此操作不可撤销。</p>
        <button
          className="rounded-md border border-red-300 bg-white px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-1"
          onClick={() => setClearDialogOpen(true)}
          disabled={clearing}
          aria-label="清除语义缓存"
        >
          清除语义缓存
        </button>
        <ConfirmDialog
          open={clearDialogOpen}
          onOpenChange={setClearDialogOpen}
          title="确认清除语义缓存"
          description="清除后所有缓存的语义匹配结果将被删除，后续请求将重新生成回答。确定要继续吗？"
          onConfirm={handleClearCache}
          confirmLabel="确认清除"
        />
      </section>

      {/* ── Embed Code Generator ── */}
      <section className={sectionClass} aria-label="嵌入代码生成器">
        <h2 className="mb-4 text-lg font-medium text-gray-800">嵌入代码生成器</h2>
        <div className="mb-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <label htmlFor="embedApiKey" className={labelClass}>API Key</label>
            <input
              id="embedApiKey"
              type="text"
              className={inputClass}
              value={embedApiKey}
              onChange={(e) => setEmbedApiKey(e.target.value)}
              placeholder="ck_xxx"
            />
          </div>
          <div>
            <label htmlFor="embedTheme" className={labelClass}>主题</label>
            <select id="embedTheme" className={inputClass} value={embedTheme} onChange={(e) => setEmbedTheme(e.target.value as 'light' | 'dark')}>
              <option value="light">Light</option>
              <option value="dark">Dark</option>
            </select>
          </div>
          <div>
            <label htmlFor="embedPosition" className={labelClass}>位置</label>
            <select id="embedPosition" className={inputClass} value={embedPosition} onChange={(e) => setEmbedPosition(e.target.value as 'bottom-right' | 'bottom-left')}>
              <option value="bottom-right">右下角</option>
              <option value="bottom-left">左下角</option>
            </select>
          </div>
          <div>
            <label htmlFor="embedLang" className={labelClass}>语言</label>
            <select id="embedLang" className={inputClass} value={embedLang} onChange={(e) => setEmbedLang(e.target.value as 'zh-CN' | 'en')}>
              <option value="zh-CN">中文</option>
              <option value="en">English</option>
            </select>
          </div>
        </div>
        <div className="relative">
          <pre className="overflow-x-auto rounded-md bg-gray-900 p-4 text-sm text-green-400">
            <code>{embedSnippet}</code>
          </pre>
          <button
            className="absolute right-2 top-2 rounded bg-gray-700 px-3 py-1 text-xs text-white hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
            onClick={handleCopySnippet}
            aria-label="复制嵌入代码"
          >
            {copied ? '已复制' : '复制'}
          </button>
        </div>
      </section>
    </div>
  );
}
