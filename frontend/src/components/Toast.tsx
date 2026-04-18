import { useState, useCallback, createContext, useContext, type ReactNode } from 'react';
// eslint-disable-next-line react-refresh/only-export-components
import * as ToastPrimitive from '@radix-ui/react-toast';
import { registerToast } from './toast-utils';

export type { ToastType } from './toast-utils';

interface ToastItem {
  id: string;
  type: ToastType;
  message: string;
}

interface ToastContextValue {
  showToast: (type: ToastType, message: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}

const typeStyles: Record<ToastType, string> = {
  success: 'border-green-500 bg-green-50 text-green-900',
  error: 'border-red-500 bg-red-50 text-red-900',
  info: 'border-blue-500 bg-blue-50 text-blue-900',
};

const typeLabels: Record<ToastType, string> = {
  success: '成功提示',
  error: '错误提示',
  info: '信息提示',
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const showToastHandler = useCallback((type: ToastType, message: string) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    setToasts((prev) => [...prev, { id, type, message }]);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  // Register the toast function for use outside React tree
  useState(() => {
    registerToast(showToastHandler);
  });

  return (
    <ToastContext.Provider value={{ showToast: showToastHandler }}>
      <ToastPrimitive.Provider swipeDirection="right">
        {children}
        {toasts.map((toast) => (
          <ToastPrimitive.Root
            key={toast.id}
            open
            onOpenChange={(open) => { if (!open) removeToast(toast.id); }}
            duration={4000}
            className={`rounded-lg border-l-4 px-4 py-3 shadow-md ${typeStyles[toast.type]}`}
            aria-label={typeLabels[toast.type]}
          >
            <ToastPrimitive.Description className="text-sm">
              {toast.message}
            </ToastPrimitive.Description>
            <ToastPrimitive.Close
              className="absolute right-2 top-2 rounded p-1 opacity-70 hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-offset-1"
              aria-label="关闭通知"
            >
              ✕
            </ToastPrimitive.Close>
          </ToastPrimitive.Root>
        ))}
        <ToastPrimitive.Viewport
          className="fixed bottom-4 right-4 z-50 flex w-80 flex-col gap-2"
          aria-label="通知列表"
        />
      </ToastPrimitive.Provider>
    </ToastContext.Provider>
  );
}
