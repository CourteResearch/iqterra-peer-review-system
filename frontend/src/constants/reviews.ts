/**
 * Review-related constants
 */

import type { Review, NavItem, RubricItem } from '../types';

export const INITIAL_REVIEWS: Review[] = [
  {
    id: '4172',
    title: 'Designing for equitable peer learning',
    author: 'Anonymous student',
    course: 'ICT801A · Project proposal',
    due: 'Due in 2 days',
    status: 'Ready to review',
    initials: 'PR',
    tint: 'mint',
  },
  {
    id: '4198',
    title: 'A scalable feedback model for large cohorts',
    author: 'Anonymous student',
    course: 'ICT801A · Project proposal',
    due: 'Due in 2 days',
    status: 'In progress',
    initials: 'FE',
    tint: 'lavender',
  },
  {
    id: '4201',
    title: 'Building trust into the assessment process',
    author: 'Anonymous student',
    course: 'ICT801A · Project proposal',
    due: 'Due in 2 days',
    status: 'Ready to review',
    initials: 'TR',
    tint: 'peach',
  },
];

export const NAV_ITEMS: NavItem[] = [
  { name: 'Overview', icon: '▦' },
  { name: 'Reviews', icon: '▤' },
  { name: 'Allocation', icon: '◫' },
  { name: 'Moderation', icon: '⚑' },
  { name: 'Gradebook', icon: '▧' },
  { name: 'Settings', icon: '⚙' },
];

export const RUBRIC: RubricItem[] = [
  { title: 'Problem framing', note: 'Is the challenge clear, relevant and well scoped?' },
  { title: 'Evidence and sources', note: 'Are claims supported by appropriate evidence?' },
  { title: 'Method and feasibility', note: 'Can the proposed approach be carried out?' },
  { title: 'Communication', note: 'Is the proposal coherent and easy to follow?' },
];