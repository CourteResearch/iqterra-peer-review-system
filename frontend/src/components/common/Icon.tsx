/**
 * Icon component for navigation and UI icons
 */

interface IconProps {
  children: React.ReactNode;
  className?: string;
}

export function Icon({ children, className = '' }: IconProps) {
  return <span className={`nav-icon ${className}`.trim()} aria-hidden="true">{children}</span>;
}