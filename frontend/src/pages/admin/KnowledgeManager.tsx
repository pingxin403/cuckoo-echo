import { useEffect, useRef, useState, useCallback, type DragEvent, type ChangeEvent } from 'react';
import { useKnowledgeStore } from '@/stores/adminStore';
import { validateFile } from '@/lib/fileValidation';
import { showToast } from '@/components/Toast';
import { ConfirmDialog } from '@/components/ConfirmDialog';
import { Skeleton } from '@/components/Skeleton';
import apiClient from '@/network/axios';
import type { KnowledgeDoc, DocStatus } from '@/types';

/* ── Status helpers ── */

const STATUS_LABELS: Record<DocStatus, string> = {
  pending: '等待处理',
  processing: '处理中',
  completed: '已完成',
  failed: '失败',
};

const STATUS_COLORS: Record<DocStatus, string> = {
  pending: 'bg-yellow-50 text-yellow-700',
  processing: 'bg-blue-50 text-blue-700',
  completed: 'bg-green-50 text-green-700',
  failed: 'bg-red-50 text-red-700',
};

const FILTER_OPTIONS: { label: string; value: DocStatus | 'all' }[] = [
  { label: '全部', value: 'all' },
  { label: '等待处理', value: 'pending' },
  { label: '处理中', value: 'processing' },
  { label: '已完成', value: 'completed' },
  { label: '失败', value: 'failed' },
];

/* ── Polling hook ── */

function useProcessingPoller(documents: KnowledgeDoc[]) {
  const timersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());
  const delaysRef = useRef<Map<string, number>>(new Map());
  const { fetchDocuments } = useKnowledgeStore();

  const poll = useCallback(
    (docId: string) => {
      const delay = delaysRef.current.get(docId) ?? 3000;
      const timer = setTimeout(async () => {
        try {
          await fetchDocuments();
        } catch {
          // handled by interceptor
        }
        // Schedule next poll with exponential backoff
        const nextDelay = Math.min(delay * 2, 15000);
        delaysRef.current.set(docId, nextDelay);
        // Re-check will happen via the effect below
      }, delay);
      timersRef.current.set(docId, timer);
    },
    [fetchDocuments],
  );

  useEffect(() => {
    // Clear all existing timers
    for (const timer of timersRef.current.values()) clearTimeout(timer);
    timersRef.current.clear();

    // Start polling for processing docs
    const processingDocs = documents.filter(
      (d) => d.status === 'pending' || d.status === 'processing',
    );
    for (const doc of processingDocs) {
      if (!delaysRef.current.has(doc.id)) {
        delaysRef.current.set(doc.id, 3000);
      }
      poll(doc.id);
    }

    // Clean up delays for completed/failed docs
    for (const [id] of delaysRef.current) {
      const doc = documents.find((d) => d.id === id);
      if (!doc || doc.status === 'completed' || doc.status === 'failed') {
        delaysRef.current.delete(id);
      }
    }

    return () => {
      for (const timer of timersRef.current.values()) clearTimeout(timer);
      timersRef.current.clear();
    };
  }, [documents, poll]);
}

/* ── Main component ── */

export default function KnowledgeManager() {
  const {
    documents,
    docFilter,
    isLoading,
    fetchDocuments,
    uploadDocument,
    deleteDocument,
    setDocFilter,
  } = useKnowledgeStore();

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<KnowledgeDoc | null>(null);

  // Polling for processing documents
  useProcessingPoller(documents);

  // Initial fetch
  useEffect(() => {
    fetchDocuments();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* ── File handling ── */

  const handleFiles = useCallback(
    async (files: FileList | File[]) => {
      const file = files[0];
      if (!file) return;

      const { isValid, error } = validateFile(file, 'document');
      if (!isValid) {
        showToast('error', error ?? '文件校验失败');
        return;
      }

      setUploading(true);
      try {
        await uploadDocument(file);
        showToast('success', '文档上传成功');
      } catch {
        // error handled by axios interceptor
      } finally {
        setUploading(false);
      }
    },
    [uploadDocument],
  );

  const onFileSelect = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) handleFiles(e.target.files);
    e.target.value = '';
  };

  const onDragOver = (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const onDragLeave = (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files) handleFiles(e.dataTransfer.files);
  };

  /* ── Retry ── */

  const handleRetry = async (docId: string) => {
    try {
      await apiClient.post(`/admin/v1/knowledge/docs/${docId}/retry`);
      showToast('info', '已重新提交处理');
      await fetchDocuments();
    } catch {
      // handled by interceptor
    }
  };

  /* ── Delete ── */

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    try {
      await deleteDocument(deleteTarget.id);
      showToast('success', '文档已删除');
    } catch {
      // handled by interceptor
    } finally {
      setDeleteTarget(null);
    }
  };

  /* ── Filtered list ── */

  const filtered = documents.filter((doc) => {
    const matchSearch =
      !docFilter.search ||
      doc.filename.toLowerCase().includes(docFilter.search.toLowerCase());
    const matchStatus =
      docFilter.status === 'all' || doc.status === docFilter.status;
    return matchSearch && matchStatus;
  });

  /* ── Render ── */

  return (
    <div className="space-y-6">
      {/* Header */}
      <h1 className="text-xl font-semibold text-gray-900">知识库管理</h1>

      {/* Upload zone */}
      <div
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        className={`flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors ${
          isDragging
            ? 'border-indigo-500 bg-indigo-50'
            : 'border-gray-300 bg-gray-50 hover:border-gray-400'
        }`}
        role="region"
        aria-label="文档上传区域"
      >
        <p className="text-sm text-gray-600">
          {uploading ? '上传中…' : '拖拽文件到此处，或'}
        </p>
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          className="mt-2 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          aria-label="选择文件上传"
        >
          选择文件
        </button>
        <p className="mt-2 text-xs text-gray-400">
          支持 PDF、DOCX、HTML、TXT，最大 200MB
        </p>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.html,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/html,text/plain"
          onChange={onFileSelect}
          className="hidden"
          aria-hidden="true"
        />
      </div>

      {/* Search + filter */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <input
          type="text"
          placeholder="搜索文件名…"
          value={docFilter.search}
          onChange={(e) => setDocFilter({ search: e.target.value })}
          className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          aria-label="搜索文件名"
        />
        <div className="flex gap-1" role="group" aria-label="状态筛选">
          {FILTER_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setDocFilter({ status: opt.value })}
              className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                docFilter.status === opt.value
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
              aria-pressed={docFilter.status === opt.value}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Document list */}
      {isLoading && documents.length === 0 ? (
        <div className="space-y-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} variant="list" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        /* Empty state */
        <div className="flex flex-col items-center rounded-lg border border-gray-200 bg-white py-16">
          <p className="text-gray-400">暂无文档</p>
          <button
            onClick={() => fileInputRef.current?.click()}
            className="mt-4 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
            aria-label="立即上传文档"
          >
            立即上传
          </button>
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                  文件名
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                  上传时间
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                  状态
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                  分块数
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium uppercase text-gray-500">
                  操作
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.map((doc) => (
                <DocRow
                  key={doc.id}
                  doc={doc}
                  onRetry={handleRetry}
                  onDelete={setDeleteTarget}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Delete confirmation dialog */}
      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(open) => { if (!open) setDeleteTarget(null); }}
        title="删除文档"
        description={`确定要删除「${deleteTarget?.filename ?? ''}」吗？此操作不可撤销。`}
        onConfirm={confirmDelete}
        confirmLabel="删除"
        cancelLabel="取消"
      />
    </div>
  );
}

/* ── DocRow sub-component ── */

function DocRow({
  doc,
  onRetry,
  onDelete,
}: {
  doc: KnowledgeDoc;
  onRetry: (id: string) => void;
  onDelete: (doc: KnowledgeDoc) => void;
}) {
  const formattedDate = new Date(doc.createdAt).toLocaleString('zh-CN');

  return (
    <tr>
      <td className="px-4 py-3 text-sm text-gray-900">{doc.filename}</td>
      <td className="px-4 py-3 text-sm text-gray-500">{formattedDate}</td>
      <td className="px-4 py-3">
        <span
          className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[doc.status]}`}
        >
          {STATUS_LABELS[doc.status]}
        </span>
        {doc.status === 'failed' && doc.errorMsg && (
          <p className="mt-1 text-xs text-red-500">{doc.errorMsg}</p>
        )}
      </td>
      <td className="px-4 py-3 text-sm text-gray-500">{doc.chunkCount}</td>
      <td className="px-4 py-3 text-right">
        <div className="flex items-center justify-end gap-2">
          {doc.status === 'failed' && (
            <button
              onClick={() => onRetry(doc.id)}
              className="rounded px-2 py-1 text-xs font-medium text-indigo-600 hover:bg-indigo-50"
              aria-label={`重试处理 ${doc.filename}`}
            >
              重试
            </button>
          )}
          <button
            onClick={() => onDelete(doc)}
            className="rounded px-2 py-1 text-xs font-medium text-red-600 hover:bg-red-50"
            aria-label={`删除 ${doc.filename}`}
          >
            删除
          </button>
        </div>
      </td>
    </tr>
  );
}
