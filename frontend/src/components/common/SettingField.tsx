/**
 * Setting field component
 */

import type { SettingFieldProps } from '../../types';

export function SettingField({ label, value }: SettingFieldProps) {
  return (
    <label className="setting-field">
      <span>{label}</span>
      <div>{value}<i>⌄</i></div>
    </label>
  );
}