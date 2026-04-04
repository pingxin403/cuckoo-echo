import { validateFile, FILE_RULES } from '../../lib/fileValidation';

function makeFile(name: string, size: number, type: string): File {
  const buffer = new ArrayBuffer(size);
  return new File([buffer], name, { type });
}

describe('validateFile', () => {
  describe('valid files', () => {
    it('accepts a valid JPEG image', () => {
      const file = makeFile('photo.jpg', 1024, 'image/jpeg');
      expect(validateFile(file, 'image')).toEqual({ isValid: true });
    });

    it('accepts a valid PNG image', () => {
      const file = makeFile('photo.png', 2048, 'image/png');
      expect(validateFile(file, 'image')).toEqual({ isValid: true });
    });

    it('accepts a valid WebP image', () => {
      const file = makeFile('photo.webp', 512, 'image/webp');
      expect(validateFile(file, 'image')).toEqual({ isValid: true });
    });
  });

  describe('oversized files', () => {
    it('rejects image > 10MB', () => {
      const file = makeFile('big.jpg', 11 * 1024 * 1024, 'image/jpeg');
      const result = validateFile(file, 'image');
      expect(result.isValid).toBe(false);
      expect(result.error).toContain('10');
    });

    it('rejects audio > 5MB', () => {
      const file = makeFile('big.wav', 6 * 1024 * 1024, 'audio/wav');
      const result = validateFile(file, 'audio');
      expect(result.isValid).toBe(false);
      expect(result.error).toContain('5');
    });

    it('rejects document > 50MB', () => {
      const file = makeFile('big.pdf', 51 * 1024 * 1024, 'application/pdf');
      const result = validateFile(file, 'document');
      expect(result.isValid).toBe(false);
      expect(result.error).toContain('50');
    });
  });

  describe('invalid MIME types', () => {
    it('rejects unsupported image type', () => {
      const file = makeFile('photo.gif', 1024, 'image/gif');
      const result = validateFile(file, 'image');
      expect(result.isValid).toBe(false);
      expect(result.error).toBe('不支持该文件格式');
    });

    it('rejects unsupported audio type', () => {
      const file = makeFile('audio.ogg', 1024, 'audio/ogg');
      const result = validateFile(file, 'audio');
      expect(result.isValid).toBe(false);
      expect(result.error).toBe('不支持该文件格式');
    });
  });

  describe('boundary values', () => {
    it('accepts image exactly at 10MB limit', () => {
      const file = makeFile('exact.jpg', 10 * 1024 * 1024, 'image/jpeg');
      expect(validateFile(file, 'image')).toEqual({ isValid: true });
    });

    it('rejects image 1 byte over 10MB limit', () => {
      const file = makeFile('over.jpg', 10 * 1024 * 1024 + 1, 'image/jpeg');
      expect(validateFile(file, 'image').isValid).toBe(false);
    });

    it('accepts audio exactly at 5MB limit', () => {
      const file = makeFile('exact.wav', 5 * 1024 * 1024, 'audio/wav');
      expect(validateFile(file, 'audio')).toEqual({ isValid: true });
    });

    it('accepts document exactly at 50MB limit', () => {
      const file = makeFile('exact.pdf', 50 * 1024 * 1024, 'application/pdf');
      expect(validateFile(file, 'document')).toEqual({ isValid: true });
    });
  });
});
