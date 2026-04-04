import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

vi.mock('@/network/axios', () => ({
  default: { post: vi.fn() },
}));

vi.mock('@/lib/imageCompress', () => ({
  compressImage: vi.fn((file: File) => Promise.resolve(file)),
}));

vi.mock('@/components/Toast', () => ({
  showToast: vi.fn(),
}));

import MediaUploader from '@/pages/chat/MediaUploader';
import { showToast } from '@/components/Toast';

describe('MediaUploader', () => {
  const onUploadComplete = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders image and voice upload buttons', () => {
    render(<MediaUploader onUploadComplete={onUploadComplete} />);
    expect(screen.getByRole('button', { name: /选择图片上传/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /开始录音/ })).toBeInTheDocument();
  });

  it('rejects oversized image >10MB', async () => {
    render(<MediaUploader onUploadComplete={onUploadComplete} />);
    const big = new File([new ArrayBuffer(11 * 1024 * 1024)], 'big.png', { type: 'image/png' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [big] } });
    await waitFor(() => {
      expect(showToast).toHaveBeenCalledWith('error', expect.stringContaining('文件过大'));
    });
  });

  it('rejects unsupported file format', async () => {
    render(<MediaUploader onUploadComplete={onUploadComplete} />);
    const pdf = new File(['data'], 'doc.pdf', { type: 'application/pdf' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [pdf] } });
    await waitFor(() => {
      expect(showToast).toHaveBeenCalledWith('error', expect.stringContaining('不支持'));
    });
  });
});
