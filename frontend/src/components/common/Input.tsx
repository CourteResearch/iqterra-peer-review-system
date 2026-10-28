/**
 * Input component for text, textarea, and number inputs
 */

import type { InputProps } from '../../types';

export function Input({
  value,
  onChange,
  placeholder,
  type = 'text',
  className = '',
  disabled = false,
  ...props
}: InputProps) {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    onChange(e.target.value);
  };

  if (type === 'textarea') {
    return (
      <textarea
        className={`input ${className}`.trim()}
        value={value}
        onChange={handleChange}
        placeholder={placeholder}
        disabled={disabled}
        {...props}
      />
    );
  }

  return (
    <input
      className={`input ${className}`.trim()}
      type={type}
      value={value}
      onChange={handleChange}
      placeholder={placeholder}
      disabled={disabled}
      {...props}
    />
  );
}