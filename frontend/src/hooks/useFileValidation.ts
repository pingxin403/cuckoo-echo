import { useCallback, useState } from 'react';
import { validateFile } from '@/lib/fileValidation';

type FileCategory = 'image' | 'audio' | 'document';

interface UseFileValidationReturn {
  validate: (file: File) => { isValid: boolean; error?: string };
  isValid: boolean;
  error: string | null;
}

export function useFileValidation(category: FileCategory): UseFileValidationReturn {
  const [isValid, setIsValid] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const validate = useCallback(
    (file: File) => {
      const result = validateFile(file, category);
      setIsValid(result.isValid);
      setError(result.error ?? null);
      return result;
    },
    [category],
  );

  return { validate, isValid, error };
}
