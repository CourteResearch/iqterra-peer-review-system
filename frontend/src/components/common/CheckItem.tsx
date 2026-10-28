/**
 * Checklist item component
 */

import type { ChecklistItem } from '../../types';

interface CheckItemProps extends ChecklistItem {}

export function CheckItem({ done = false, label, detail, action, onClick }: CheckItemProps) {
  return (
    <div className="check-item">
      <span className={`check-circle ${done ? 'checked' : ''}`}>{done ? '✓' : ''}</span>
      <span className="check-copy">
        <b>{label}</b>
        <small>{detail}</small>
      </span>
      {action && onClick && (
        <button className="text-button" onClick={onClick}>
          {action} →
        </button>
      )}
    </div>
  );
}