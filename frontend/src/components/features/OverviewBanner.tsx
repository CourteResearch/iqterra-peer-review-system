/**
 * Overview banner component
 */

interface OverviewBannerProps {
  role: 'Instructor' | 'Student';
}

export function OverviewBanner({ role }: OverviewBannerProps) {
  return (
    <section className="overview-banner" aria-labelledby="banner-title">
      <div className="banner-copy">
        <h1 id="banner-title">
          {role === 'Instructor' ? 'Peer review workspace' : 'Your peer reviews'}
        </h1>
        <p>
          {role === 'Instructor'
            ? 'Monitor review progress, allocate reviewers, and release grades — all in one place.'
            : 'See your assigned reviews, track progress, and submit feedback.'}
        </p>
        <div className="banner-meta">
          <span className="round-strip">
            <b>Active round:</b> Project proposal peer review
            <span className="strip-progress">
              <span style={{ width: '78%' }} />
            </span>
            <small>78% complete · Due 21 Oct</small>
          </span>
          <span className="sandbox-pill">Sandbox mode</span>
        </div>
      </div>
      <div className="banner-art" aria-hidden="true">
        <svg viewBox="0 0 200 200" preserveAspectRatio="none">
          <defs>
            <linearGradient id="bannerGrad" x1="0" y1="0" x2="200" y2="200" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="var(--orange)" stopOpacity="0.15" />
              <stop offset="100%" stopColor="var(--navy)" stopOpacity="0.08" />
            </linearGradient>
          </defs>
          <rect width="200" height="200" fill="url(#bannerGrad)" />
          <circle cx="100" cy="100" r="60" fill="none" stroke="var(--orange)" strokeWidth="2" strokeDasharray="12 8" opacity="0.4" />
          <circle cx="100" cy="100" r="90" fill="none" stroke="var(--navy)" strokeWidth="1.5" strokeDasharray="8 12" opacity="0.3" />
          <circle cx="100" cy="100" r="30" fill="var(--orange)" opacity="0.2" />
        </svg>
      </div>
    </section>
  );
}