import { useState, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Message, MediaAttachment } from '@/types';
import { sanitizeHtml } from '@/lib/sanitize';
import { Skeleton } from '@/components/Skeleton';
import apiClient from '@/network/axios';
import { showToast } from '@/components/Toast';
import FeedbackPanel from './FeedbackPanel';
import ImageLightbox from './ImageLightbox';

// ── Props ──────────────────────────────────────────────────────

export interface MessageBubbleProps {
  message: Message;
  isStreaming?: boolean;
  streamingContent?: string;
}

// ── Helpers ────────────────────────────────────────────────────

function formatTimestamp(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

// ── Typing indicator (animated dots) ───────────────────────────

function TypingIndicator() {
  return (
    <span className="inline-flex items-center gap-1" aria-label="正在输入">
      <span className="h-1.5 w-1.5 rounded-full bg-gray-400 animate-bounce [animation-delay:0ms]" />
      <span className="h-1.5 w-1.5 rounded-full bg-gray-400 animate-bounce [animation-delay:150ms]" />
      <span className="h-1.5 w-1.5 rounded-full bg-gray-400 animate-bounce [animation-delay:300ms]" />
    </span>
  );
}

// ── Media renderers ────────────────────────────────────────────

function ImageAttachment({ att }: { att: MediaAttachment }) {
  const [loaded, setLoaded] = useState(false);
  const [lightboxOpen, setLightboxOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        className="relative aspect-video w-full max-w-xs overflow-hidden rounded-lg cursor-pointer focus:outline-none focus:ring-2 focus:ring-[var(--ce-primary-color,#4f46e5)]"
        onClick={() => setLightboxOpen(true)}
        aria-label="点击放大查看图片"
      >
        {!loaded && <Skeleton className="absolute inset-0" />}
        <img
          src={att.thumbnailUrl ?? att.url}
          alt="图片附件"
          loading="lazy"
          onLoad={() => setLoaded(true)}
          className={`h-full w-full object-cover transition-opacity ${loaded ? 'opacity-100' : 'opacity-0'}`}
        />
      </button>
      {lightboxOpen && (
        <ImageLightbox
          src={att.url}
          alt="图片附件"
          onClose={() => setLightboxOpen(false)}
        />
      )}
    </>
  );
}

function AudioAttachment({ att }: { att: MediaAttachment }) {
  return (
    <audio controls preload="none" className="w-full max-w-xs" aria-label="语音消息">
      <source src={att.url} type={att.mimeType} />
    </audio>
  );
}

function MediaAttachments({ attachments }: { attachments: MediaAttachment[] }) {
  if (attachments.length === 0) return null;
  return (
    <div className="mt-2 flex flex-col gap-2">
      {attachments.map((att, i) =>
        att.type === 'image' ? (
          <ImageAttachment key={`${att.url}-${i}`} att={att} />
        ) : att.type === 'audio' ? (
          <AudioAttachment key={`${att.url}-${i}`} att={att} />
        ) : null,
      )}
    </div>
  );
}

// ── Feedback buttons (assistant only) ──────────────────────────

function FeedbackButtons({
  rating,
  submitted,
  onRate,
  onThumbDown,
}: {
  rating?: 'up' | 'down' | null;
  submitted?: boolean;
  onRate: (r: 'up' | 'down') => void;
  onThumbDown: () => void;
}) {
  return (
    <span className="ml-2 inline-flex items-center gap-1">
      {submitted ? (
        <span className="text-[10px] text-green-600">已反馈 ✓</span>
      ) : (
        <>
          <button
            type="button"
            onClick={() => onRate('up')}
            className={`rounded p-0.5 text-xs transition-colors ${
              rating === 'up'
                ? 'text-green-600'
                : 'text-gray-400 hover:text-gray-600'
            }`}
            aria-label="点赞"
            aria-pressed={rating === 'up'}
          >
            👍
          </button>
          <button
            type="button"
            onClick={onThumbDown}
            className={`rounded p-0.5 text-xs transition-colors ${
              rating === 'down'
                ? 'text-red-600'
                : 'text-gray-400 hover:text-gray-600'
            }`}
            aria-label="点踩"
            aria-pressed={rating === 'down'}
          >
            👎
          </button>
        </>
      )}
    </span>
  );
}

// ── Markdown renderer with DOMPurify ───────────────────────────

function SafeMarkdown({ content }: { content: string }) {
  const clean = sanitizeHtml(content);
  return (
    <div className="prose prose-sm max-w-none break-words">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {clean}
      </ReactMarkdown>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────

export default function MessageBubble({
  message,
  isStreaming = false,
  streamingContent,
}: MessageBubbleProps) {
  const [localRating, setLocalRating] = useState<'up' | 'down' | null>(
    message.rating ?? null,
  );
  const [showFeedbackPanel, setShowFeedbackPanel] = useState(false);
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);

  const handleRate = useCallback(
    async (r: 'up' | 'down') => {
      const newRating = localRating === r ? null : r;
      setLocalRating(newRating);
      if (r === 'up' && newRating === 'up') {
        // Submit thumb-up directly
        try {
          await apiClient.post('/v1/feedback', {
            thread_id: message.threadId,
            message_id: message.id,
            rating: 'up',
            reason: '',
          });
          setFeedbackSubmitted(true);
        } catch {
          showToast('error', '反馈提交失败，请稍后重试');
          setLocalRating(null);
        }
      }
    },
    [localRating, message.threadId, message.id],
  );

  const handleThumbDown = useCallback(() => {
    setLocalRating('down');
    setShowFeedbackPanel(true);
  }, []);

  const handleFeedbackSubmitted = useCallback(() => {
    setShowFeedbackPanel(false);
    setFeedbackSubmitted(true);
  }, []);

  const isUser = message.role === 'user';
  const isAssistant = message.role === 'assistant';
  const isHumanAgent = message.role === 'human_agent';

  // Content to display: streaming content takes priority when streaming
  const displayContent =
    isStreaming && streamingContent != null ? streamingContent : message.content;

  const media = message.mediaAttachments ?? [];

  return (
    <div
      className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
      data-testid="message-bubble"
    >
      <div
        className={`relative max-w-[80%] rounded-lg px-3 py-2 text-sm ${
          isUser
            ? 'bg-[var(--ce-primary-color,#4f46e5)] text-white'
            : isHumanAgent
              ? 'bg-green-100 text-gray-900'
              : 'bg-gray-100 text-gray-900'
        }`}
      >
        {/* Human agent badge */}
        {isHumanAgent && (
          <span className="mb-1 inline-block rounded bg-green-600 px-1.5 py-0.5 text-[10px] font-medium text-white">
            人工客服
          </span>
        )}

        {/* Message body */}
        {isStreaming && !displayContent ? (
          <TypingIndicator />
        ) : isUser ? (
          <p className="whitespace-pre-wrap">{displayContent}</p>
        ) : (
          <SafeMarkdown content={displayContent} />
        )}

        {/* Media attachments */}
        {media.length > 0 && <MediaAttachments attachments={media} />}

        {/* Footer: timestamp + feedback */}
        <div className="relative mt-1 flex items-center text-[10px] opacity-60">
          <time dateTime={message.createdAt}>
            {formatTimestamp(message.createdAt)}
          </time>
          {isAssistant && !isStreaming && (
            <>
              <FeedbackButtons
                rating={localRating}
                submitted={feedbackSubmitted}
                onRate={handleRate}
                onThumbDown={handleThumbDown}
              />
              {showFeedbackPanel && (
                <FeedbackPanel
                  threadId={message.threadId}
                  messageId={message.id}
                  onClose={() => setShowFeedbackPanel(false)}
                  onSubmitted={handleFeedbackSubmitted}
                />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
