/**
 * Gradebook page component
 */

import { useState } from 'react';
import { GradebookTable } from '../components/features';
import { CheckItem } from '../components/common';
import { Panel } from '../components/common';
import { GRADE_STUDENTS, GRADE_METRICS, GRADE_CHECKLIST } from '../constants/gradebook';
import { MetricGrid } from '../components/features';
import type { View } from '../types';

export function GradebookPage() {
  const [releaseMode, setReleaseMode] = useState<'Manual' | 'Automatic'>('Manual');
  const [confirmed, setConfirmed] = useState(false);
  const [released, setReleased] = useState(false);

  const handleView = (student: string) => {
    console.log(`View grade details for ${student}`);
    alert(`View grade details for ${student}`);
  };

  const handleRelease = () => {
    if (confirmed && !released) {
      setReleased(true);
      alert('Grades released to Moodle!');
    }
  };

  const handleConfirm = () => {
    setConfirmed(true);
  };

  return (
    <div className="gradebook-page">
      <div className="page-heading">
        <div>
          <h1>Gradebook</h1>
          <p>Final scores and grade release to Moodle</p>
        </div>
        <div className="heading-actions">
          <div className="release-mode-selector">
            <label>
              Release mode:
              <select
                value={releaseMode}
                onChange={(e) => setReleaseMode(e.target.value as 'Manual' | 'Automatic')}
                className="release-select"
              >
                <option value="Manual">Manual</option>
                <option value="Automatic">Automatic</option>
              </select>
            </label>
            <small>{releaseMode === 'Manual' ? 'You control the release' : 'Only the final assessment score will be sent to the Moodle gradebook.'}</small>
          </div>
          {released ? (
            <span className="released-badge">✓ Released</span>
          ) : confirmed ? (
            <button className="button button-primary" onClick={handleRelease}>
              Review and release <span>→</span>
            </button>
          ) : (
            <button className="button button-primary" onClick={handleConfirm}>
              Review and release <span>→</span>
            </button>
          )}
        </div>
      </div>
      <MetricGrid metrics={GRADE_METRICS} className="grade-metrics" />
      <div className="gradebook-content">
        <GradebookTable students={GRADE_STUDENTS} onView={handleView} />
        <Panel title="Grade release checklist" subtitle="Complete these steps before sending scores">
          <div className="check-progress">2 of 3 complete</div>
          {GRADE_CHECKLIST.map((item, index) => (
            <CheckItem key={index} {...item} />
          ))}
          {confirmed && !released && (
            <div className="modal-backdrop" onClick={() => setConfirmed(false)}>
              <div className="modal-content release-confirm">
                <h2>Confirm grade release</h2>
                <p>This will send final scores for 44 students to the Moodle gradebook for ICT801A · Peer review.</p>
                <p><b>This action cannot be undone.</b></p>
                <div className="modal-actions">
                  <button className="button button-secondary" onClick={() => setConfirmed(false)}>Cancel</button>
                  <button className="button button-primary" onClick={handleRelease}>Confirm release</button>
                </div>
              </div>
            </div>
          )}
        </Panel>
      </div>
    </div>
  );
}