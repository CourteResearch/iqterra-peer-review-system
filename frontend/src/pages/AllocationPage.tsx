/**
 * Allocation page component
 */

import { AllocationTable } from '../components/features';
import { ALLOCATION_ROWS } from '../constants/allocation';
import type { View } from '../types';

export function AllocationPage() {
  const handleReallocate = (student: string) => {
    console.log(`Reallocate reviewers for ${student}`);
    alert(`Reallocate reviewers for ${student}`);
  };

  return (
    <div className="allocation-page">
      <div className="page-heading">
        <div>
          <h1>Allocation</h1>
          <p>Configure reviewer assignments and monitor completion</p>
        </div>
        <div className="heading-actions">
          <button className="button button-secondary">Export</button>
          <button className="button button-primary">
            <span>Auto-allocate</span>
            <span>→</span>
          </button>
        </div>
      </div>
      <div className="allocation-content">
        <div className="allocation-info">
          <h2>Current allocation</h2>
          <p>Each student is assigned 3 reviewers. Reviewers are assigned automatically based on availability and expertise.</p>
          <div className="allocation-stats">
            <div className="stat">
              <b>48</b> <small>Students</small>
            </div>
            <div className="stat">
              <b>144</b> <small>Total reviews</small>
            </div>
            <div className="stat">
              <b>78%</b> <small>Completion rate</small>
            </div>
            <div className="stat">
              <b>3</b> <small>Need attention</small>
            </div>
          </div>
        </div>
        <AllocationTable rows={ALLOCATION_ROWS} onReallocate={handleReallocate} />
      </div>
    </div>
  );
}