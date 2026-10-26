/**
 * Badge component for status indicators
 */

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info';
  className?: string;
}

export function Badge({ children, variant = 'default', className = '' }: BadgeProps) {
  const variantClasses = variant !== 'default' ? `badge-${variant}` : '';
  return <span className={`badge ${variantClasses} ${className}`.trim()}>{children}</span>;
}