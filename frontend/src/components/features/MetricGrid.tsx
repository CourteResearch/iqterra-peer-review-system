/**
 * Metric grid component for displaying dashboard metrics
 */

import { MetricCard } from '../common';
import type { MetricData } from '../../types';

interface MetricGridProps {
  metrics: MetricData[];
  className?: string;
}

export function MetricGrid({ metrics, className = '' }: MetricGridProps) {
  return (
    <div className={`metric-grid ${className}`.trim()} role="region" aria-label="Key metrics">
      {metrics.map((metric, index) => (
        <MetricCard key={metric.label + index} data={metric} />
      ))}
    </div>
  );
}