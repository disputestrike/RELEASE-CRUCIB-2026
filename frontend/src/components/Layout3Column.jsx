import React, { useState } from 'react';
import { Menu, X, PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import Logo from './Logo';
import './Layout3Column.css';

/**
 * 3-Column Layout Component (Manus-inspired)
 * 
 * Structure:
 * - Left Sidebar (240px fixed)
 * - Main Content (flexible)
 * - Right Panel (320px fixed)
 * 
 * Responsive:
 * - Mobile: Single column (sidebar hidden)
 * - Tablet: 2 columns (sidebar collapsible)
 * - Desktop: 3 columns (all visible)
 */

export const Layout3Column = ({
  sidebar,
  main,
  rightPanel,
  className = '',
  sidebarOpen: controlledSidebarOpen,
  onToggleSidebar,
  setSidebarOpen: setControlledSidebarOpen,
  hideSidebarToggle = false,
}) => {
  const [internalSidebarOpen, setInternalSidebarOpen] = useState(true);
  const [rightPanelOpen, setRightPanelOpen] = useState(true);

  const sidebarOpen = controlledSidebarOpen !== undefined ? controlledSidebarOpen : internalSidebarOpen;
  const setSidebarOpen = setControlledSidebarOpen || setInternalSidebarOpen;
  const handleToggleSidebar = onToggleSidebar || (() => setSidebarOpen(prev => !prev));

  return (
    <div className={`layout-3-column app-shell ${className}`}>
      {/* Mobile Header */}
      <div className="layout-mobile-header">
        <button
          className="layout-toggle-sidebar"
          onClick={handleToggleSidebar}
          aria-label="Toggle sidebar"
        >
          {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
        <Logo variant="full" height={28} href="/app" className="layout-mobile-title" showTagline={false} />
        <button
          className="layout-toggle-panel"
          onClick={() => setRightPanelOpen(!rightPanelOpen)}
          aria-label="Toggle right panel"
        >
          {rightPanelOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      {/* Main Layout Container */}
      <div className="layout-container">
        {/* Left Sidebar — collapsible; toggle handle always visible */}
        <div className="layout-sidebar-wrapper">
          <aside
            className={`layout-sidebar ${sidebarOpen ? 'open' : 'closed'}`}
            role="navigation"
          >
            <div className="layout-sidebar-content">
              {sidebar}
            </div>
          </aside>
          <button
            type="button"
            className="layout-sidebar-toggle"
            onClick={handleToggleSidebar}
            aria-label={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
            title={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
            style={{ display: hideSidebarToggle ? 'none' : undefined }}
          >
            {sidebarOpen ? <PanelLeftClose size={18} /> : <PanelLeftOpen size={18} />}
          </button>
        </div>

        {/* Main Content Area (Flexible) — full width when no right panel */}
        <main className={`layout-main ${!rightPanel ? 'layout-main--full' : ''}`}>
          <div className="layout-main-content">
            {main}
          </div>
        </main>

        {/* Right Panel (380px) — only rendered when there is content */}
        {rightPanel != null && (
          <aside
            className={`layout-right-panel ${rightPanelOpen ? 'open' : 'closed'}`}
            role="complementary"
          >
            <div className="layout-panel-content">
              {rightPanel}
            </div>
          </aside>
        )}
      </div>

      {/* Mobile Overlay — hide with CSS, never remove from DOM */}
      {rightPanel != null && (sidebarOpen || rightPanelOpen) && (
        <div
          className="layout-overlay"
          onClick={() => {
            setSidebarOpen(false);
            setRightPanelOpen(false);
          }}
          aria-hidden
        />
      )}
    </div>
  );
};

export default Layout3Column;
