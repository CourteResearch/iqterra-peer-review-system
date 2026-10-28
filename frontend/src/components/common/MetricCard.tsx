/**
 * Metric card component for dashboard metrics
 */

import type { MetricData } from '../../types';

interface MetricCardProps {
  data: MetricData;
}

export function MetricCard({ data }: MetricCardProps) {
  return (
    <div className="metric-card">
      <div className="metric-icon" style={{ backgroundColor: `var(--${data.accent})` }}>
        <span aria-hidden="true">{data.icon}</span>
      </div>
      <div className="metric-content">
        <div className="metric-value">{data.value}</div>
        <div className="metric-label">{data.label}</div>
        <div className="metric-detail">{data.detail}</div>
      </div>
    </div>
  );
}