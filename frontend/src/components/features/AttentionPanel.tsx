/**
 * Attention panel component for items needing attention
 */

import { Button } from '../common';
import type { AttentionItem } from '../../types';

interface AttentionPanelProps {
  items: AttentionItem[];
}

export function AttentionPanel({ items }: AttentionPanelProps) {
  return (
    <section className="attention-panel panel" aria-labelledby="attention-title">
      <div className="panel-heading">
        <div>
          <h2 id="attention-title">Needs attention</h2>
          <p>Items requiring your action</p>
        </div>
      </div>
      <div className="panel-body">
        <ul className="attention-list" role="list">
          {items.map((item, index) => (
            <li key={index} className={`attention-item attention-${item.type}`}>
              <div className="attention-icon" aria-hidden="true">
                {item.type === 'warning' && '⚠'}
                {item.type === 'info' && 'ℹ'}
                {item.type === 'alert' && '⚑'}
              </div>
              <div className="attention-content">
                <h3>{item.title}</h3>
                <p>{item.detail}</p>
              </div>
              {item.action && item.onClick && (
                <Button variant="secondary" size="sm" onClick={item.onClick}>
                  {item.action}
                </Button>
              )}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}