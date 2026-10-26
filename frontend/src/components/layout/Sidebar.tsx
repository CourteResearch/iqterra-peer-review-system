/**
 * Sidebar navigation component
 */

import { useState } from 'react';
import { NAV_ITEMS } from '../../constants';
import type { View, NavItem } from '../../types';
import { Icon } from '../common';

interface SidebarProps {
  currentView: View;
  onViewChange: (view: View) => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
}

export function Sidebar({ currentView, onViewChange, collapsed, onToggleCollapse }: SidebarProps) {
  return (
    <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
      <div className="brand">
        <div className="brand-mark">
          <span />
        </div>
        {!collapsed && (
          <div className="brand-name">
            IQTerra
            <span>Peer Review</span>
          </div>
        )}
        <button className="collapse" onClick={onToggleCollapse} aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}>
          {collapsed ? '▸' : '◂'}
        </button>
      </div>

      {!collapsed && (
        <>
          <div className="workspace-label">Workspace</div>
          <div className="course-switch">
            <div className="course-symbol">PR</div>
            <div className="course-text">
              <b>Project proposal peer review</b>
              <small>ICT801A · Semester 2, 2026</small>
            </div>
            <span className="chevron">›</span>
          </div>
        </>
      )}

      <nav className="main-nav" aria-label="Main navigation">
        {!collapsed && <div className="nav-label">Views</div>}
        <ul className="nav-list">
          {NAV_ITEMS.map((item: NavItem) => (
            <li key={item.name}>
              <button
                className={`nav-item ${currentView === item.name ? 'active' : ''}`}
                onClick={() => onViewChange(item.name)}
                aria-current={currentView === item.name ? 'page' : undefined}
              >
                <Icon>{item.icon}</Icon>
                {!collapsed && <span>{item.name}</span>}
              </button>
            </li>
          ))}
        </ul>
      </nav>

      {!collapsed && (
        <div className="sidebar-bottom">
          <div className="help-card">
            <span className="help-icon">?</span>
            <div className="help-text">
              <b>Need help?</b>
              <small>Visit our help center or contact support</small>
            </div>
          </div>
          <div className="user-menu">
            <div className="user-avatar" style={{ background: 'var(--orange)' }}>JD</div>
            <div className="user-copy">
              <b>John Doe</b>
              <small>Instructor</small>
            </div>
            <div className="dots" aria-hidden="true">
              <span />
              <span />
              <span />
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}