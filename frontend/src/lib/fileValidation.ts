interface ValidationRule {
  maxSizeMb: number;
  allowedTypes: string[];
}

export const FILE_RULES: Record<string, ValidationRule> = {
  image: {
    maxSizeMb: 10,
    allowedTypes: ['image/jpeg', 'image/png', 'image/webp'],
  },
  audio: {
    maxSizeMb: 5,
    allowedTypes: ['audio/wav', 'audio/mpeg', 'audio/mp4'],
  },
  document: {
    maxSizeMb: 50,
    allowedTypes: [
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'text/html',
      'text/plain',
    ],
  },
};

export function validateFile(
  file: File,
  category: 'image' | 'audio' | 'document',
): { isValid: boolean; error?: string } {
  const rule = FILE_RULES[category];
  if (!rule.allowedTypes.includes(file.type)) {
    return { isValid: false, error: '不支持该文件格式' };
  }
  if (file.size > rule.maxSizeMb * 1024 * 1024) {
    return { isValid: false, error: `文件过大，最大支持 ${rule.maxSizeMb} MB` };
  }
  return { isValid: true };
}
