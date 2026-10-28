/**
 * Type definitions for the IQTerra Peer Review application
 */

export type View =
  | 'Overview'
  | 'Reviews'
  | 'Allocation'
  | 'Moderation'
  | 'Gradebook'
  | 'Settings';

export type Role = 'Instructor' | 'Student';

export type ReviewStatus = 'Ready to review' | 'In progress' | 'Submitted';

export interface Review {
  id: string;
  title: string;
  author: string;
  course: string;
  due: string;
  status: ReviewStatus;
  initials: string;
  tint: string;
}

export interface NavItem {
  name: View;
  icon: string;
}

export interface RubricItem {
  title: string;
  note: string;
}

export interface Person {
  initials: string;
  name: string;
  completed: string;
  assigned: string;
  status: string;
  tint: string;
}

export interface MetricData {
  label: string;
  value: string;
  detail: string;
  icon: string;
  accent: string;
}

export interface ActivityItem {
  time: string;
  description: string;
  type: string;
}

export interface AttentionItem {
  type: string;
  title: string;
  detail: string;
  action: string;
  onClick: () => void;
}

export interface ChartData {
  labels: string[];
  datasets: Array<{
    label: string;
    data: number[];
    color: string;
  }>;
}

export interface ProgressRow {
  initials: string;
  name: string;
  completed: string;
  score: string;
  status: string;
  tint: string;
}

export interface AllocationRow {
  student: string;
  reviewers: string;
  assigned: string;
  completed: string;
  action: string;
}

export interface ModerationFlag {
  id: string;
  reviewer: string;
  reviewee: string;
  issue: string;
  severity: 'low' | 'medium' | 'high';
  status: 'open' | 'resolved';
}

export interface GradeStudent {
  name: string;
  reviews: string;
  score: string;
  status: string;
  action: string;
}

export interface ChecklistItem {
  done: boolean;
  label: string;
  detail: string;
  action?: string;
  onClick?: () => void;
}

export interface SettingFieldProps {
  label: string;
  value: string;
}

export interface ToggleProps {
  checked: boolean;
  onClick: () => void;
}

export interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  onClick?: () => void;
  children: React.ReactNode;
  className?: string;
}

export interface InputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  type?: 'text' | 'textarea' | 'number';
  className?: string;
  disabled?: boolean;
}

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}

export interface ToastProps {
  message: string;
  onClose: () => void;
}

export interface PanelProps {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  headingAction?: React.ReactNode;
}
