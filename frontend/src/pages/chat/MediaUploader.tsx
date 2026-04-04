import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type DragEvent,
  type ClipboardEvent,
} from 'react';
import { useFileValidation } from '@/hooks/useFileValidation';
import { compressImage } from '@/lib/imageCompress';
import { showToast } from '@/components/Toast';
import apiClient from '@/network/axios';
import type { MediaAttachment } from '@/types';

// ── Props ──────────────────────────────────────────────────────

export interface MediaUploaderProps {
  onUploadComplete: (attachment: MediaAttachment) => void;
  disabled?: boolean;
}

// ── Constants ──────────────────────────────────────────────────

const MAX_RECORD_SECONDS = 60;
const IMAGE_ACCEPT = 'image/jpeg,image/png,image/webp';

type RecordingState = 'idle' | 'recording' | 'paused' | 'preview';

// ── Component ──────────────────────────────────────────────────

export default function MediaUploader({
  onUploadComplete,
  disabled = false,
}: MediaUploaderProps) {
  // ── Image upload state ──
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [preview, setPreview] = useState<{ type: 'image' | 'audio'; url: string } | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── Voice recording state ──
  const [recordingState, setRecordingState] = useState<RecordingState>('idle');
  const [recordSeconds, setRecordSeconds] = useState(0);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Validation hooks ──
  const imageValidation = useFileValidation('image');
  const audioValidation = useFileValidation('audio');

  // ── Cleanup object URLs on unmount ──
  useEffect(() => {
    return () => {
      if (audioUrl) URL.revokeObjectURL(audioUrl);
      if (preview?.url.startsWith('blob:')) URL.revokeObjectURL(preview.url);
    };
  }, [audioUrl, preview]);

  // ── Upload file to server ──
  const uploadFile = useCallback(
    async (file: File, type: 'image' | 'audio') => {
      setUploadProgress(0);
      const formData = new FormData();
      formData.append('file', file);
      formData.append('type', type);

      try {
        const res = await apiClient.post<MediaAttachment>('/v1/media/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
          onUploadProgress: (e) => {
            if (e.total) {
              setUploadProgress(Math.round((e.loaded / e.total) * 100));
            }
          },
        });
        setUploadProgress(null);
        onUploadComplete(res.data);
      } catch {
        setUploadProgress(null);
        showToast('error', '上传失败，请重试');
      }
    },
    [onUploadComplete],
  );

  // ── Process image file (validate → compress → preview → upload) ──
  const processImageFile = useCallback(
    async (file: File) => {
      const result = imageValidation.validate(file);
      if (!result.isValid) {
        showToast('error', result.error ?? '文件校验失败');
        return;
      }

      const compressed = await compressImage(file);
      const objectUrl = URL.createObjectURL(compressed);
      setPreview({ type: 'image', url: objectUrl });
      await uploadFile(compressed, 'image');
    },
    [imageValidation, uploadFile],
  );

  // ── Image: click to select ──
  const handleImageClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) void processImageFile(file);
      // Reset so same file can be re-selected
      if (fileInputRef.current) fileInputRef.current.value = '';
    },
    [processImageFile],
  );

  // ── Image: drag & drop ──
  const handleDragOver = useCallback((e: DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file && file.type.startsWith('image/')) {
        void processImageFile(file);
      }
    },
    [processImageFile],
  );

  // ── Image: paste (Ctrl+V / Cmd+V) ──
  const handlePaste = useCallback(
    (e: ClipboardEvent) => {
      const items = e.clipboardData.items;
      for (let i = 0; i < items.length; i++) {
        if (items[i].type.startsWith('image/')) {
          const file = items[i].getAsFile();
          if (file) {
            e.preventDefault();
            void processImageFile(file);
            return;
          }
        }
      }
    },
    [processImageFile],
  );

  // ── Voice: timer helpers ──
  const startTimer = useCallback(() => {
    timerRef.current = setInterval(() => {
      setRecordSeconds((prev) => {
        if (prev >= MAX_RECORD_SECONDS - 1) {
          // Auto-stop at 60s — handled in effect
          return MAX_RECORD_SECONDS;
        }
        return prev + 1;
      });
    }, 1000);
  }, []);

  const stopTimer = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  // ── Auto-stop recording at max duration ──
  useEffect(() => {
    if (recordSeconds >= MAX_RECORD_SECONDS && recordingState === 'recording') {
      mediaRecorderRef.current?.stop();
      stopTimer();
    }
  }, [recordSeconds, recordingState, stopTimer]);

  // ── Voice: start recording ──
  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/mp4' });
        setAudioBlob(blob);
        const url = URL.createObjectURL(blob);
        setAudioUrl(url);
        setRecordingState('preview');
        // Stop all tracks
        stream.getTracks().forEach((t) => t.stop());
      };

      recorder.start();
      setRecordSeconds(0);
      setRecordingState('recording');
      startTimer();
    } catch {
      showToast('error', '无法访问麦克风，请检查权限');
    }
  }, [startTimer]);

  // ── Voice: pause ──
  const pauseRecording = useCallback(() => {
    mediaRecorderRef.current?.pause();
    setRecordingState('paused');
    stopTimer();
  }, [stopTimer]);

  // ── Voice: resume ──
  const resumeRecording = useCallback(() => {
    mediaRecorderRef.current?.resume();
    setRecordingState('recording');
    startTimer();
  }, [startTimer]);

  // ── Voice: complete ──
  const completeRecording = useCallback(() => {
    mediaRecorderRef.current?.stop();
    stopTimer();
  }, [stopTimer]);

  // ── Voice: cancel ──
  const cancelRecording = useCallback(() => {
    mediaRecorderRef.current?.stop();
    stopTimer();
    setRecordingState('idle');
    setRecordSeconds(0);
    setAudioBlob(null);
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
      setAudioUrl(null);
    }
    // Stop tracks
    mediaRecorderRef.current?.stream?.getTracks().forEach((t) => t.stop());
  }, [stopTimer, audioUrl]);

  // ── Voice: upload recorded audio ──
  const uploadAudio = useCallback(async () => {
    if (!audioBlob) return;
    const file = new File([audioBlob], `recording-${Date.now()}.m4a`, {
      type: 'audio/mp4',
    });
    const result = audioValidation.validate(file);
    if (!result.isValid) {
      showToast('error', result.error ?? '文件校验失败');
      return;
    }
    setPreview({ type: 'audio', url: audioUrl ?? '' });
    setRecordingState('idle');
    setRecordSeconds(0);
    await uploadFile(file, 'audio');
    setAudioBlob(null);
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
      setAudioUrl(null);
    }
  }, [audioBlob, audioUrl, audioValidation, uploadFile]);

  // ── Format seconds as mm:ss ──
  const formatTime = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
  };

  return (
    <div
      className="space-y-2"
      onPaste={handlePaste}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      aria-label="媒体上传"
    >
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept={IMAGE_ACCEPT}
        className="hidden"
        onChange={handleFileChange}
        aria-hidden="true"
      />

      {/* Drag overlay */}
      {isDragging && (
        <div className="rounded-lg border-2 border-dashed border-blue-400 bg-blue-50 p-4 text-center text-sm text-blue-600">
          松开以上传图片
        </div>
      )}

      {/* Action buttons row */}
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={handleImageClick}
          disabled={disabled || uploadProgress !== null}
          className="rounded-md border border-gray-300 px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-50 disabled:opacity-40"
          aria-label="选择图片上传"
        >
          📷 图片
        </button>

        {recordingState === 'idle' && (
          <button
            type="button"
            onClick={() => void startRecording()}
            disabled={disabled || uploadProgress !== null}
            className="rounded-md border border-gray-300 px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-50 disabled:opacity-40"
            aria-label="开始录音"
          >
            🎤 录音
          </button>
        )}
      </div>

      {/* Voice recording controls */}
      {(recordingState === 'recording' || recordingState === 'paused') && (
        <div className="flex items-center gap-2 rounded-lg bg-gray-50 p-2">
          <span
            className={`h-2 w-2 rounded-full ${recordingState === 'recording' ? 'animate-pulse bg-red-500' : 'bg-yellow-500'}`}
            aria-hidden="true"
          />
          <span className="text-xs font-mono text-gray-700" aria-live="polite">
            {formatTime(recordSeconds)} / {formatTime(MAX_RECORD_SECONDS)}
          </span>

          {recordingState === 'recording' ? (
            <button
              type="button"
              onClick={pauseRecording}
              className="rounded px-2 py-1 text-xs text-gray-600 hover:bg-gray-200"
              aria-label="暂停录音"
            >
              ⏸ 暂停
            </button>
          ) : (
            <button
              type="button"
              onClick={resumeRecording}
              className="rounded px-2 py-1 text-xs text-gray-600 hover:bg-gray-200"
              aria-label="继续录音"
            >
              ▶ 继续
            </button>
          )}

          <button
            type="button"
            onClick={completeRecording}
            className="rounded px-2 py-1 text-xs text-green-700 hover:bg-green-100"
            aria-label="完成录音"
          >
            ✓ 完成
          </button>

          <button
            type="button"
            onClick={cancelRecording}
            className="rounded px-2 py-1 text-xs text-red-600 hover:bg-red-100"
            aria-label="取消录音"
          >
            ✕ 取消
          </button>
        </div>
      )}

      {/* Voice preview & upload */}
      {recordingState === 'preview' && audioUrl && (
        <div className="flex items-center gap-2 rounded-lg bg-gray-50 p-2">
          <audio src={audioUrl} controls className="h-8 flex-1" aria-label="录音预览" />
          <button
            type="button"
            onClick={() => void uploadAudio()}
            disabled={disabled}
            className="rounded-md bg-[var(--ce-primary-color,#4f46e5)] px-3 py-1 text-xs text-white hover:opacity-90 disabled:opacity-40"
            aria-label="发送录音"
          >
            发送
          </button>
          <button
            type="button"
            onClick={cancelRecording}
            className="rounded px-2 py-1 text-xs text-red-600 hover:bg-red-100"
            aria-label="重录"
          >
            重录
          </button>
        </div>
      )}

      {/* Upload progress bar */}
      {uploadProgress !== null && (
        <div className="space-y-1" aria-label="上传进度">
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-gray-200">
            <div
              className="h-full rounded-full bg-[var(--ce-primary-color,#4f46e5)] transition-all"
              style={{ width: `${uploadProgress}%` }}
              role="progressbar"
              aria-valuenow={uploadProgress}
              aria-valuemin={0}
              aria-valuemax={100}
            />
          </div>
          <p className="text-xs text-gray-500">{uploadProgress}%</p>
        </div>
      )}

      {/* Completed preview */}
      {preview && uploadProgress === null && (
        <div className="rounded-lg bg-gray-50 p-2">
          {preview.type === 'image' ? (
            <img
              src={preview.url}
              alt="上传预览"
              className="max-h-32 rounded object-cover"
            />
          ) : (
            <audio src={preview.url} controls className="h-8 w-full" aria-label="已上传音频" />
          )}
        </div>
      )}
    </div>
  );
}
