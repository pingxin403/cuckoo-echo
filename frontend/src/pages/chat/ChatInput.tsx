import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
  type ChangeEvent,
} from 'react';
import type { MediaAttachment } from '@/types';
import MediaUploader from '@/pages/chat/MediaUploader';

// ── Props ──────────────────────────────────────────────────────

export interface ChatInputProps {
  onSend: (content: string, media?: MediaAttachment[]) => void;
  disabled?: boolean;
}

// ── Constants ──────────────────────────────────────────────────

const MAX_ROWS = 4;
const LINE_HEIGHT_PX = 24;
const PADDING_PX = 16; // py-2 = 8px * 2

// ── Component ──────────────────────────────────────────────────

export default function ChatInput({ onSend, disabled = false }: ChatInputProps) {
  const [text, setText] = useState('');
  const [showUploader, setShowUploader] = useState(false);
  const [pendingMedia, setPendingMedia] = useState<MediaAttachment[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const handleMediaUpload = useCallback((attachment: MediaAttachment) => {
    setPendingMedia((prev) => [...prev, attachment]);
    setShowUploader(false);
  }, []);

  // ── Auto-resize textarea (up to MAX_ROWS lines) ──
  const resizeTextarea = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    const maxHeight = LINE_HEIGHT_PX * MAX_ROWS + PADDING_PX;
    el.style.height = `${Math.min(el.scrollHeight, maxHeight)}px`;
  }, []);

  const handleChange = useCallback(
    (e: ChangeEvent<HTMLTextAreaElement>) => {
      setText(e.target.value);
      resizeTextarea();
    },
    [resizeTextarea],
  );

  // ── Keyboard: Enter to send, Shift+Enter for newline ──
  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (disabled) return;
        const trimmed = text.trim();
        if (!trimmed && pendingMedia.length === 0) return;
        onSend(trimmed, pendingMedia.length > 0 ? pendingMedia : undefined);
        setText('');
        setPendingMedia([]);
        // Reset height after clearing
        requestAnimationFrame(() => {
          if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
          }
        });
      }
    },
    [disabled, text, onSend, pendingMedia],
  );

  const handleSendClick = useCallback(() => {
    if (disabled) return;
    const trimmed = text.trim();
    if (!trimmed && pendingMedia.length === 0) return;
    onSend(trimmed, pendingMedia.length > 0 ? pendingMedia : undefined);
    setText('');
    setPendingMedia([]);
    requestAnimationFrame(() => {
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    });
  }, [disabled, text, onSend, pendingMedia]);

  // ── Mobile: visualViewport handling for soft keyboard ──
  useEffect(() => {
    const vv = window.visualViewport;
    if (!vv) return;

    const handleResize = () => {
      const container = containerRef.current;
      if (!container) return;
      // Offset the input container so it stays above the soft keyboard
      const offsetBottom = window.innerHeight - vv.height - vv.offsetTop;
      container.style.transform =
        offsetBottom > 0 ? `translateY(-${offsetBottom}px)` : '';
    };

    vv.addEventListener('resize', handleResize);
    vv.addEventListener('scroll', handleResize);
    return () => {
      vv.removeEventListener('resize', handleResize);
      vv.removeEventListener('scroll', handleResize);
    };
  }, []);

  const canSend = (text.trim().length > 0 || pendingMedia.length > 0) && !disabled;

  return (
    <div
      ref={containerRef}
      className="border-t border-gray-200 bg-white px-3 py-2 transition-transform"
      aria-label="消息输入"
    >
      {/* Disabled hint */}
      {disabled && (
        <p className="mb-1 text-xs text-gray-400" aria-live="polite">
          AI 正在思考…
        </p>
      )}

      <div className="flex items-end gap-2">
        {/* Media upload toggle */}
        <button
          type="button"
          onClick={() => setShowUploader((v) => !v)}
          className={`flex-shrink-0 rounded p-1.5 transition-colors disabled:opacity-40 ${
            showUploader ? 'text-[var(--ce-primary-color,#4f46e5)]' : 'text-gray-400 hover:text-gray-600'
          }`}
          disabled={disabled}
          aria-label="上传图片"
          title="上传图片/语音"
        >
          {/* Image icon (SVG) */}
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="h-5 w-5"
          >
            <path
              fillRule="evenodd"
              d="M1 5.25A2.25 2.25 0 0 1 3.25 3h13.5A2.25 2.25 0 0 1 19 5.25v9.5A2.25 2.25 0 0 1 16.75 17H3.25A2.25 2.25 0 0 1 1 14.75v-9.5Zm1.5 9.5c0 .414.336.75.75.75h13.5a.75.75 0 0 0 .75-.75v-2.3l-2.72-2.72a.75.75 0 0 0-1.06 0L9.5 13.19l-2.22-2.22a.75.75 0 0 0-1.06 0L2.5 14.69v.06ZM12 8.5a1.5 1.5 0 1 1 3 0 1.5 1.5 0 0 1-3 0Z"
              clipRule="evenodd"
            />
          </svg>
        </button>

        {/* Textarea */}
        <textarea
          ref={textareaRef}
          value={text}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          rows={1}
          placeholder={disabled ? 'AI 正在思考…' : '输入消息…'}
          className="min-h-[40px] flex-1 resize-none rounded-lg border border-gray-300 bg-gray-50 px-3 py-2 text-sm leading-6 outline-none transition-colors placeholder:text-gray-400 focus:border-[var(--ce-primary-color,#4f46e5)] focus:ring-1 focus:ring-[var(--ce-primary-color,#4f46e5)] disabled:cursor-not-allowed disabled:opacity-50"
          aria-label="消息输入框"
          style={{ lineHeight: `${LINE_HEIGHT_PX}px` }}
        />

        {/* Send button */}
        <button
          type="button"
          onClick={handleSendClick}
          disabled={!canSend}
          className="flex-shrink-0 rounded-lg bg-[var(--ce-primary-color,#4f46e5)] p-2 text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
          aria-label="发送消息"
        >
          {/* Send icon (SVG) */}
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="h-5 w-5"
          >
            <path d="M3.105 2.288a.75.75 0 0 0-.826.95l1.414 4.926A1.5 1.5 0 0 0 5.135 9.25h6.115a.75.75 0 0 1 0 1.5H5.135a1.5 1.5 0 0 0-1.442 1.086l-1.414 4.926a.75.75 0 0 0 .826.95 28.897 28.897 0 0 0 15.293-7.154.75.75 0 0 0 0-1.115A28.897 28.897 0 0 0 3.105 2.288Z" />
          </svg>
        </button>
      </div>

      {/* Pending media preview */}
      {pendingMedia.length > 0 && (
        <div className="mt-2 flex gap-2">
          {pendingMedia.map((m, i) => (
            <div key={i} className="relative">
              {m.type === 'image' ? (
                <img src={m.thumbnailUrl ?? m.url} alt="待发送图片" className="h-12 w-12 rounded object-cover" />
              ) : (
                <span className="inline-block rounded bg-gray-100 px-2 py-1 text-xs text-gray-600">🎤 语音</span>
              )}
              <button
                type="button"
                onClick={() => setPendingMedia((prev) => prev.filter((_, j) => j !== i))}
                className="absolute -right-1 -top-1 h-4 w-4 rounded-full bg-red-500 text-[10px] leading-4 text-white"
                aria-label="移除附件"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}

      {/* MediaUploader panel */}
      {showUploader && (
        <div className="mt-2">
          <MediaUploader onUploadComplete={handleMediaUpload} disabled={disabled} />
        </div>
      )}
    </div>
  );
}
