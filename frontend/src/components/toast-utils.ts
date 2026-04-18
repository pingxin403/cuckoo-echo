// Toast utility functions for use outside React tree (e.g., Axios interceptors)
import type { ToastType } from './Toast';

let _showToast: ((type: ToastType, message: string) => void) | null = null;

export function registerToast(fn: (type: ToastType, message: string) => void) {
  _showToast = fn;
}

export function showToast(type: ToastType, message: string) {
  if (_showToast) {
    _showToast(type, message);
  } else {
    console.warn('[Toast] ToastProvider not mounted yet');
  }
}

export type { ToastType };