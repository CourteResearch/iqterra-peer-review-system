/**
 * Moderation flags table component
 */

import { Button, Badge } from '../common';
import type { ModerationFlag } from '../../types';

interface ModerationFlagsProps {
  flags: ModerationFlag[];
  onReview: (flag: ModerationFlag) => void;
  onResolve: (flag: ModerationFlag) => void;
}

export function ModerationFlags({ flags, onReview, onResolve }: ModerationFlagsProps) {
  const severityColors: Record<string, string> = {
    high: 'var(--coral)',
    medium: 'var(--amber)',
    low: 'var(--blue)',
  };

  return (
    <div className="moderation-table" role="table" aria-label="Moderation flags">
      <div className="table-head" role="row">
        <span role="columnheader">ID</span>
        <span role="columnheader">Reviewer</span>
        <span role="columnheader">Reviewee</span>
        <span role="columnheader">Issue</span>
        <span role="columnheader">Severity</span>
        <span role="columnheader">Status</span>
        <span role="columnheader">Actions</span>
      </div>
      {flags.map((flag, index) => (
        <div key={index} className="table-row" role="row">
          <span role="cell">{flag.id}</span>
          <span role="cell">{flag.reviewer}</span>
          <span role="cell">{flag.reviewee}</span>
          <span role="cell">{flag.issue}</span>
          <span role="cell">
            <Badge variant={flag.severity as 'error' | 'warning' | 'info'}>
              {flag.severity}
            </Badge>
          </span>
          <span role="cell">
            <Badge variant={flag.status === 'open' ? 'warning' : 'success'}>
              {flag.status}
            </Badge>
          </span>
          <span role="cell">
            <div className="action-buttons">
              <Button variant="secondary" size="sm" onClick={() => onReview(flag)}>
                Review
              </Button>
              {flag.status === 'open' && (
                <Button variant="primary" size="sm" onClick={() => onResolve(flag)}>
                  Resolve
                </Button>
              )}
            </div>
          </span>
        </div>
      ))}
    </div>
  );
}