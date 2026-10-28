/**
 * Top header/navigation bar component
 */

import type { View } from '../../types';

interface HeaderProps {
  currentView: View;
  role: 'Instructor' | 'Student';
  onRoleChange: (role: 'Instructor' | 'Student') => void;
  sandbox: boolean;
  onSandboxToggle: () => void;
}

export function Header({ currentView, role, onRoleChange, sandbox, onSandboxToggle }: HeaderProps) {
  const viewTitles: Record<View, { title: string; description: string }> = {
    Overview: { title: 'Overview', description: 'Peer review workspace dashboard' },
    Reviews: { title: 'Reviews', description: 'Manage and monitor review rounds' },
    Allocation: { title: 'Allocation', description: 'Configure reviewer assignments' },
    Moderation: { title: 'Moderation', description: 'Review flagged submissions' },
    Gradebook: { title: 'Gradebook', description: 'Final scores and grade release' },
    Settings: { title: 'Settings', description: 'Configure review round details' },
  };

  const { title, description } = viewTitles[currentView];

  return (
    <header className="topbar">
      <div className="breadcrumbs">
        <span>IQTerra</span>
        <span aria-hidden="true">/</span>
        <span>Peer Review</span>
        <span aria-hidden="true">/</span>
        <span>{title}</span>
      </div>
      <div className="top-actions">
        <div className="role-switcher">
          <button
            className={`sandbox-pill ${role === 'Instructor' ? 'active' : ''}`}
            onClick={() => onRoleChange('Instructor')}
          >
            Instructor
          </button>
          <button
            className={`sandbox-pill ${role === 'Student' ? 'active' : ''}`}
            onClick={() => onRoleChange('Student')}
          >
            Student view
          </button>
        </div>
        {sandbox && <span className="sandbox-pill badge-info">Sandbox</span>}
        <button className="button button-secondary" onClick={onSandboxToggle}>
          <span>{sandbox ? 'Exit sandbox' : 'Enter sandbox'}</span>
        </button>
      </div>
    </header>
  );
}