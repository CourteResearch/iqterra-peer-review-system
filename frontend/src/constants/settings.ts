/**
 * Settings page constants
 */

export const SETTINGS_TABS = [
  'Round details',
  'Rubric',
  'Privacy and blinding',
  'Notifications',
];

export const TINT_COLORS = {
  mint: 'var(--mint)',
  lavender: 'var(--lavender)',
  peach: 'var(--peach)',
  blue: 'var(--blue)',
  amber: 'var(--amber)',
  coral: 'var(--coral)',
  purple: 'var(--purple)',
  green: 'var(--green)',
} as const;

export const STATUS_COLORS = {
  'Ready to review': 'var(--mint)',
  'In progress': 'var(--blue)',
  Submitted: 'var(--lavender)',
  Complete: 'var(--mint)',
  'In progress': 'var(--blue)',
  'Needs attention': 'var(--amber)',
  Pending: 'var(--blue)',
  'Needs review': 'var(--amber)',
  Incomplete: 'var(--coral)',
  Ready: 'var(--mint)',
} as const;