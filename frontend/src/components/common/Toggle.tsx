/**
 * Toggle switch component
 */

import type { ToggleProps } from '../../types';

export function Toggle({ checked, onClick }: ToggleProps) {
  return (
    <button
      className={`toggle ${checked ? 'on' : ''}`}
      role="switch"
      aria-checked={checked}
      onClick={onClick}
    >
      <i />
    </button>
  );
}