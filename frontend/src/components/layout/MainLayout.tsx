/**
 * Main layout component composing sidebar, header, content area, and footer
 */

import type { View } from '../../types';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { Footer } from './Footer';

interface MainLayoutProps {
  currentView: View;
  onViewChange: (view: View) => void;
  role: 'Instructor' | 'Student';
  onRoleChange: (role: 'Instructor' | 'Student') => void;
  sandbox: boolean;
  onSandboxToggle: () => void;
  children: React.ReactNode;
  sidebarCollapsed: boolean;
  onToggleSidebar: () => void;
}

export function MainLayout({
  currentView,
  onViewChange,
  role,
  onRoleChange,
  sandbox,
  onSandboxToggle,
  children,
  sidebarCollapsed,
  onToggleSidebar,
}: MainLayoutProps) {
  return (
    <div className="app-shell">
      <Sidebar
        currentView={currentView}
        onViewChange={onViewChange}
        collapsed={sidebarCollapsed}
        onToggleCollapse={onToggleSidebar}
      />
      <main className="main-area" style={{ marginLeft: sidebarCollapsed ? '66px' : '252px' }}>
        <Header
          currentView={currentView}
          role={role}
          onRoleChange={onRoleChange}
          sandbox={sandbox}
          onSandboxToggle={onSandboxToggle}
        />
        <div className="content-wrap">{children}</div>
        <Footer currentView={currentView} sandbox={sandbox} />
      </main>
    </div>
  );
}