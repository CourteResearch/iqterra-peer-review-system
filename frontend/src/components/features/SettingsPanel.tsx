/**
 * Settings panel component
 */

import { useState } from 'react';
import { Button, Toggle, SettingField, Panel } from '../common';
import { SETTINGS_TABS } from '../../constants';
import type { ChecklistItem } from '../../types';

interface SettingsPanelProps {
  notify: (message: string) => void;
}

export function SettingsPanel({ notify }: SettingsPanelProps) {
  const [activeTab, setActiveTab] = useState(0);
  const [minWords, setMinWords] = useState(60);
  const [doubleBlind, setDoubleBlind] = useState(true);

  const tabs = SETTINGS_TABS;

  return (
    <div className="settings-grid">
      <div className="settings-side">
        {tabs.map((tab, index) => (
          <button
            key={tab}
            className={`settings-tab ${index === activeTab ? 'active' : ''}`}
            onClick={() => {
              setActiveTab(index);
              notify(`${tab} settings selected`);
            }}
          >
            {tab}
          </button>
        ))}
      </div>
      <div className="settings-content">
        {activeTab === 0 && (
          <Panel title="Review round details" subtitle="Configure the learner experience for this round.">
            <SettingField label="Round name" value="Project proposal peer review" />
            <SettingField label="Moodle course" value="ICT801A · Semester 2, 2026" />
            <div className="setting-row">
              <div>
                <b>Double blind review</b>
                <small>Hide author and reviewer identities from each other.</small>
              </div>
              <Toggle checked={doubleBlind} onClick={() => { setDoubleBlind(!doubleBlind); notify('Double blind setting updated.'); }} />
            </div>
            <div className="setting-row">
              <div>
                <b>Minimum comment length</b>
                <small>Require reviewers to write a useful written comment.</small>
              </div>
              <div className="number-control">
                <button onClick={() => { setMinWords(Math.max(10, minWords - 10)); notify('Minimum length decreased.'); }}>−</button>
                <b>{minWords}</b>
                <span>words</span>
                <button onClick={() => { setMinWords(minWords + 10); notify('Minimum length increased.'); }}>＋</button>
              </div>
            </div>
            <SettingField label="Review deadline" value="21 October 2026 · 11:59 PM" />
            <div className="settings-actions">
              <span>Changes save to this review round.</span>
              <Button variant="primary" onClick={() => notify('Round settings saved.')}>
                Save changes
              </Button>
            </div>
          </Panel>
        )}
        {activeTab === 1 && (
          <Panel title="Rubric settings" subtitle="Configure scoring criteria for peer reviews.">
            <p>Rubric configuration would go here.</p>
            <Button variant="primary" onClick={() => notify('Rubric saved.')}>
              Save rubric
            </Button>
          </Panel>
        )}
        {activeTab === 2 && (
          <Panel title="Privacy and blinding" subtitle="Configure anonymity and data visibility settings.">
            <p>Privacy settings would go here.</p>
            <Button variant="primary" onClick={() => notify('Privacy settings saved.')}>
              Save privacy settings
            </Button>
          </Panel>
        )}
        {activeTab === 3 && (
          <Panel title="Notifications" subtitle="Configure email and in-app notification preferences.">
            <p>Notification settings would go here.</p>
            <Button variant="primary" onClick={() => notify('Notification settings saved.')}>
              Save notification settings
            </Button>
          </Panel>
        )}
      </div>
    </div>
  );
}