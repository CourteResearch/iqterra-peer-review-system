/**
 * Gradebook page constants
 */

import type { MetricData, GradeStudent, ChecklistItem } from '../types';

export const GRADE_STUDENTS: GradeStudent[] = [
  ['Ava Chen', '3 / 3', '87%', 'Ready', 'View'],
  ['Noah Williams', '2 / 3', '72%', 'Pending', 'View'],
  ['Maya Patel', '3 / 3', '91%', 'Ready', 'View'],
  ['Leo Martin', '1 / 3', '58%', 'Needs review', 'View'],
  ['Amara Okafor', '3 / 3', '84%', 'Ready', 'View'],
  ['Ethan Brooks', '0 / 3', '—', 'Incomplete', 'View'],
  ['Sofia Kim', '3 / 3', '89%', 'Ready', 'View'],
  ['Oliver James', '2 / 3', '76%', 'Pending', 'View'],
];

export const GRADE_METRICS: MetricData[] = [
  { label: 'Students with final scores', value: '44 / 48', detail: '4 grades still need a review', icon: '♙', accent: 'coral' },
  { label: 'Awaiting moderation', value: '3', detail: 'Resolve flags before release', icon: '⚑', accent: 'purple' },
  { label: 'Grade destination', value: 'Moodle', detail: 'ICT801A · Peer review', icon: '↗', accent: 'green' },
  { label: 'Release mode', value: 'Manual', detail: 'You control the release', icon: '◷', accent: 'blue' },
];

export const GRADE_CHECKLIST: ChecklistItem[] = [
  { done: true, label: 'All peer reviews are submitted', detail: '144 allocated reviews across 48 students' },
  { done: true, label: 'Final score calculated for each student', detail: 'Scores use the instructor-configured rubric' },
  { done: false, label: 'Moderation flags resolved', detail: '3 flagged reviews need a decision', action: 'Review flags', onClick: () => console.log('Review flags clicked') },
];