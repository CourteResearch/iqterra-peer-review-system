/**
 * Panel component with heading and optional action
 */

import type { PanelProps } from '../../types';

export function Panel({ title, subtitle, children, headingAction }: PanelProps) {
  return (
    <div className="panel">
      <div className="panel-heading">
        <div>
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
        {headingAction && <div className="panel-heading-action">{headingAction}</div>}
      </div>
      <div className="panel-body">{children}</div>
    </div>
  );
}