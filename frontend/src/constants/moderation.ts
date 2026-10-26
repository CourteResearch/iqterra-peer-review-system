/**
 * Moderation page constants
 */

import type { ModerationFlag } from '../types';

export const MODERATION_FLAGS: ModerationFlag[] = [
  { id: 'MF-001', reviewer: 'Noah Williams', reviewee: 'Ava Chen', issue: 'Potential plagiarism detected in feedback', severity: 'high', status: 'open' },
  { id: 'MF-002', reviewer: 'Leo Martin', reviewee: 'Maya Patel', issue: 'Biased language in review comments', severity: 'medium', status: 'open' },
  { id: 'MF-003', reviewer: 'Ethan Brooks', reviewee: 'Noah Williams', issue: 'Incomplete feedback — below minimum word count', severity: 'low', status: 'resolved' },
];