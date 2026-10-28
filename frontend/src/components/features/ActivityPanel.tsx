/**
 * Activity panel component for recent activity feed
 */

import type { ActivityItem } from '../../types';

interface ActivityPanelProps {
  items: ActivityItem[];
}

export function ActivityPanel({ items }: ActivityPanelProps) {
  return (
    <section className="activity-panel panel" aria-labelledby="activity-title">
      <div className="panel-heading">
        <div>
          <h2 id="activity-title">Recent activity</h2>
          <p>Latest actions across the review workspace</p>
        </div>
      </div>
      <div className="panel-body">
        <ul className="activity-list" role="list">
          {items.map((item, index) => (
            <li key={index} className="activity-item">
              <span className="activity-time">{item.time}</span>
              <div className="activity-content">
                <p className="activity-description">{item.description}</p>
                <span className={`activity-type activity-type-${item.type}`}>{item.type}</span>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}