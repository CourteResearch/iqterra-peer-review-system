/**
 * Toast notification component
 */

import type { ToastProps } from '../../types';

export function Toast({ message, onClose }: ToastProps) {
  if (!message) return null;

  return (
    <div className="toast" role="alert" aria-live="polite">
      <span>{message}</span>
      <button className="toast-close" onClick={onClose} aria-label="Dismiss notification">
        ×
      </button>
    </div>
  );
}