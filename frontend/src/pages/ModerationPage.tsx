/**
 * Moderation page component
 */

import { ModerationFlags } from '../components/features';
import { MODERATION_FLAGS } from '../constants/moderation';
import { Panel } from '../components/common';
import type { ModerationFlag } from '../types';

export function ModerationPage() {
  const handleReview = (flag: ModerationFlag) => {
    console.log(`Review flag ${flag.id}`);
    alert(`Review flag ${flag.id}: ${flag.issue}`);
  };

  const handleResolve = (flag: ModerationFlag) => {
    console.log(`Resolve flag ${flag.id}`);
    alert(`Flag ${flag.id} resolved.`);
  };

  return (
    <div className="moderation-page">
      <div className="page-heading">
        <div>
          <h1>Moderation</h1>
          <p>Review and resolve flagged submissions</p>
        </div>
      </div>
      <div className="moderation-content">
        <div className="moderation-stats">
          <div className="stat-card open">
            <span className="stat-value">2</span>
            <span className="stat-label">Open flags</span>
          </div>
          <div className="stat-card resolved">
            <span className="stat-value">1</span>
            <span className="stat-label">Resolved</span>
          </div>
          <div className="stat-card high">
            <span className="stat-value">1</span>
            <span className="stat-label">High severity</span>
          </div>
        </div>
        <ModerationFlags flags={MODERATION_FLAGS} onReview={handleReview} onResolve={handleResolve} />
        <Panel title="Moderation guidelines" subtitle="Best practices for reviewing flagged content.">
          <ul className="guidelines-list">
            <li><b>Plagiarism:</b> Compare flagged text with source material. Request clarification from reviewer.</li>
            <li><b>Bias:</b> Assess if language shows prejudice. Consider reviewer history and context.</li>
            <li><b>Incomplete feedback:</b> Check against minimum requirements. Allow resubmission if appropriate.</li>
            <li><b>Resolution:</b> Document decision rationale. Notify affected parties of outcome.</li>
          </ul>
        </Panel>
      </div>
    </div>
  );
}