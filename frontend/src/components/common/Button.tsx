/**
 * Button component with multiple variants and sizes
 */

import type { ButtonProps } from '../../types';

export function Button({
  variant = 'primary',
  size = 'md',
  disabled = false,
  onClick,
  children,
  className = '',
  ...props
}: ButtonProps) {
  const baseClasses = 'button';
  const variantClasses = `button-${variant}`;
  const sizeClasses = size !== 'md' ? `button-${size}` : '';
  const disabledClasses = disabled ? 'button-disabled' : '';

  return (
    <button
      className={`${baseClasses} ${variantClasses} ${sizeClasses} ${disabledClasses} ${className}`.trim()}
      disabled={disabled}
      onClick={onClick}
      {...props}
    >
      {children}
    </button>
  );
}