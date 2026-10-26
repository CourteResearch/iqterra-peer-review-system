/**
 * Overview page component
 */

import { OverviewBanner, MetricGrid, ActivityPanel, AttentionPanel, ProgressPanel } from '../components/features';
import { OVERVIEW_METRICS, ACTIVITY_ITEMS, ATTENTION_ITEMS, CHART_DATA } from '../constants/overview';
import { PROGRESS_ROWS } from '../constants/people';
import type { View } from '../types';

interface OverviewPageProps {
  role: 'Instructor' | 'Student';
}

export function OverviewPage({ role }: OverviewPageProps) {
  return (
    <div className="overview-page">
      <OverviewBanner role={role} />
      <MetricGrid metrics={OVERVIEW_METRICS} />
      <div className="overview-grid">
        <ProgressPanel rows={PROGRESS_ROWS} chartData={CHART_DATA} />
        <div className="overview-side">
          <ActivityPanel items={ACTIVITY_ITEMS} />
          <AttentionPanel items={ATTENTION_ITEMS} />
        </div>
      </div>
    </div>
  );
}