/**
 * WaveformIndicator — animated waveform bars shown during ASR (voice recognition) stage.
 *
 * Renders 5 vertical bars that animate at staggered intervals to give the
 * impression of an audio waveform being processed.
 *
 * 需求: 2.4, 补充-语音波形指示器
 */
export default function WaveformIndicator({ label = '语音识别中…' }: { label?: string }) {
  return (
    <div className="flex items-center gap-2" role="status" aria-label={label}>
      <div className="flex items-end gap-0.5 h-5">
        {[0, 1, 2, 3, 4].map((i) => (
          <span
            key={i}
            className="w-1 rounded-full bg-[var(--ce-primary-color,#6366f1)] animate-waveform"
            style={{
              animationDelay: `${i * 120}ms`,
              height: '40%',
            }}
          />
        ))}
      </div>
      <span className="text-xs text-gray-500">{label}</span>
    </div>
  );
}
