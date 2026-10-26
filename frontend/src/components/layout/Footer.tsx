/**
 * Footer component
 */

interface FooterProps {
  currentView: string;
  sandbox: boolean;
}

export function Footer({ currentView, sandbox }: FooterProps) {
  const viewDescriptions: Record<string, string> = {
    Overview: 'Dashboard showing active reviews, allocation stats, and recent activity.',
    Reviews: 'Manage review rounds, track progress, and view submissions.',
    Allocation: 'Configure reviewer assignments and monitor completion.',
    Moderation: 'Review and resolve flagged submissions.',
    Gradebook: 'Calculate final scores and release grades to Moodle.',
    Settings: 'Configure review round details, rubric, and notifications.',
  };

  return (
    <footer className="main-footer">
      <div className="footer-left">
        <span className="version-badge">v0.1.0</span>
        <span className="view-hint">{viewDescriptions[currentView] || ''}</span>
      </div>
      <div className="footer-right">
        <button className="button button-ghost" onClick={() => console.log('Help clicked')}>
          Help center
        </button>
        <button className="button button-ghost" onClick={() => console.log('Feedback clicked')}>
          Send feedback
        </button>
        {sandbox && (
          <button className="button button-primary" onClick={() => console.log('Exit sandbox clicked')}>
            Exit sandbox
          </button>
        )}
      </div>
    </footer>
  );
}