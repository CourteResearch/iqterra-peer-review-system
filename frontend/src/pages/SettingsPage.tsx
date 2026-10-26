/**
 * Settings page component
 */

import { SettingsPanel } from '../components/features';
import type { View } from '../types';

export function SettingsPage() {
  const notify = (message: string) => {
    console.log(message);
    // In a real app, this would show a toast notification
  };

  return (
    <div className="settings-page">
      <div className="page-heading">
        <div>
          <h1>Settings</h1>
          <p>Configure review round details, rubric, and notifications</p>
        </div>
      </div>
      <SettingsPanel notify={notify} />
    </div>
  );
}