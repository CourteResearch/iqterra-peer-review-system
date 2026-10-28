/**
 * Overview page constants
 */

import type { MetricData, ActivityItem, AttentionItem, ChartData } from '../types';

export const OVERVIEW_METRICS: MetricData[] = [
  { label: 'Active reviews', value: '3', detail: '2 ready · 1 in progress', icon: '▤', accent: 'mint' },
  { label: 'Students allocated', value: '48', detail: 'Across 4 review rounds', icon: '♙', accent: 'blue' },
  { label: 'Completion rate', value: '78%', detail: 'Above cohort average of 72%', icon: '▲', accent: 'coral' },
  { label: 'Flags needing review', value: '3', detail: 'Go to Moderation to resolve', icon: '⚑', accent: 'purple' },
];

export const ACTIVITY_ITEMS: ActivityItem[] = [
  { time: '14 min ago', description: 'Noah Williams started reviewing "Designing for equitable peer learning"', type: 'started' },
  { time: '32 min ago', description: 'Maya Patel submitted review for "Building trust into the assessment process"', type: 'submitted' },
  { time: '1 hour ago', description: 'New review round "Project proposal peer review" created', type: 'created' },
  { time: '3 hours ago', description: 'Leo Martin flagged a review for moderation', type: 'flagged' },
  { time: '5 hours ago', description: 'Allocation updated for ICT801A cohort', type: 'allocated' },
];

export const ATTENTION_ITEMS: AttentionItem[] = [
  {
    type: 'warning',
    title: 'Leo Martin — Needs attention',
    detail: 'Only 1 of 3 reviews completed. Deadline in 2 days.',
    action: 'Send reminder',
    onClick: () => console.log('Send reminder clicked'),
  },
  {
    type: 'info',
    title: 'Ethan Brooks — In progress',
    detail: '2 of 3 reviews started, 0 completed. May need support.',
    action: 'View progress',
    onClick: () => console.log('View progress clicked'),
  },
  {
    type: 'alert',
    title: '3 moderation flags pending',
    detail: 'Reviews flagged for plagiarism, bias, and incomplete feedback.',
    action: 'Go to Moderation',
    onClick: () => console.log('Go to Moderation clicked'),
  },
];

export const CHART_DATA: ChartData = {
  labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
  datasets: [
    { label: 'Reviews submitted', data: [12, 19, 8, 24, 15, 6, 3], color: 'var(--orange)' },
    { label: 'Reviews started', data: [18, 22, 14, 28, 20, 9, 5], color: 'var(--navy)' },
  ],
};