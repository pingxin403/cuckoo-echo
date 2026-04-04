const COMPRESS_THRESHOLD = 2 * 1024 * 1024; // 2MB
const WEBP_QUALITY = 0.8;

/**
 * Compress an image file using Canvas API.
 * Files > 2MB are converted to WebP at quality 0.8.
 * Files ≤ 2MB are returned as-is.
 */
export async function compressImage(file: File): Promise<File> {
  if (file.size <= COMPRESS_THRESHOLD) {
    return file;
  }

  const bitmap = await createImageBitmap(file);
  const canvas = new OffscreenCanvas(bitmap.width, bitmap.height);
  const ctx = canvas.getContext('2d');
  if (!ctx) {
    return file;
  }

  ctx.drawImage(bitmap, 0, 0);
  bitmap.close();

  const blob = await canvas.convertToBlob({
    type: 'image/webp',
    quality: WEBP_QUALITY,
  });

  return new File([blob], file.name.replace(/\.\w+$/, '.webp'), {
    type: 'image/webp',
    lastModified: Date.now(),
  });
}
