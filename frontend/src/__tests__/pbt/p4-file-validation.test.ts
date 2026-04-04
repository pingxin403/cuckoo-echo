// Feature: frontend-ui, Property 4: 文件上传客户端校验幂等性
// **Validates: Requirements 2.1, 2.6, 5.6**

import fc from 'fast-check';
import { validateFile, FILE_RULES } from '../../lib/fileValidation';

const CATEGORIES = ['image', 'audio', 'document'] as const;
type Category = (typeof CATEGORIES)[number];

/** All allowed MIME types across all categories */
const ALL_ALLOWED_TYPES = Object.values(FILE_RULES).flatMap((r) => r.allowedTypes);

/** Random MIME types that are NOT in any allowed list */
const DISALLOWED_TYPES = [
  'image/gif',
  'image/bmp',
  'image/svg+xml',
  'audio/ogg',
  'audio/flac',
  'video/mp4',
  'application/json',
  'text/csv',
  'application/zip',
  'application/octet-stream',
];

function makeFile(size: number, type: string): File {
  // Create a real File, then override size to avoid allocating huge buffers
  const file = new File([new ArrayBuffer(0)], 'test-file', { type });
  Object.defineProperty(file, 'size', { value: size, writable: false });
  return file;
}

describe('Property 4: 文件上传客户端校验幂等性', () => {
  it('calling validateFile twice on the same file returns identical results', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 100 * 1024 * 1024 }),
        fc.oneof(
          fc.constantFrom(...ALL_ALLOWED_TYPES),
          fc.constantFrom(...DISALLOWED_TYPES),
        ),
        fc.constantFrom(...CATEGORIES),
        (size, mimeType, category) => {
          const file = makeFile(size, mimeType);
          const result1 = validateFile(file, category);
          const result2 = validateFile(file, category);

          // Idempotency: both calls return identical results
          expect(result1.isValid).toBe(result2.isValid);
          expect(result1.error).toBe(result2.error);
        },
      ),
      { numRuns: 200 },
    );
  });

  it('file size over limit → isValid=false', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...CATEGORIES),
        (category) => {
          const rule = FILE_RULES[category];
          const allowedType = rule.allowedTypes[0];
          const overSize = rule.maxSizeMb * 1024 * 1024 + 1;
          const file = makeFile(overSize, allowedType);
          const result = validateFile(file, category);

          expect(result.isValid).toBe(false);
          expect(result.error).toBeDefined();
        },
      ),
      { numRuns: 100 },
    );
  });

  it('file type not in allowed list → isValid=false', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(...CATEGORIES),
        fc.constantFrom(...DISALLOWED_TYPES),
        (category, mimeType) => {
          // Ensure the MIME type is truly not allowed for this category
          const rule = FILE_RULES[category];
          if (rule.allowedTypes.includes(mimeType)) return; // skip if accidentally allowed

          const file = makeFile(1024, mimeType);
          const result = validateFile(file, category);

          expect(result.isValid).toBe(false);
          expect(result.error).toBe('不支持该文件格式');
        },
      ),
      { numRuns: 100 },
    );
  });
});
