import React, { useState } from 'react';
import { Menu, X } from 'lucide-react';
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
}) => {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [rightPanelOpen, setRightPanelOpen] = useState(true);

  return (
    <div className={`layout-3-column ${className}`}>
      {/* Mobile Header */}
      <div className="layout-mobile-header">
        <button
          className="layout-toggle-sidebar"
          onClick={() => setSidebarOpen(!sidebarOpen)}
          aria-label="Toggle sidebar"
        >
          {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
        <div className="layout-mobile-title">CrucibAI</div>
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
        {/* Left Sidebar (240px) */}
        <aside
          className={`layout-sidebar ${sidebarOpen ? 'open' : 'closed'}`}
          role="navigation"
        >
          <div className="layout-sidebar-content">
            {sidebar}
          </div>
        </aside>

        {/* Main Content Area (Flexible) */}
        <main className="layout-main">
          <div className="layout-main-content">
            {main}
          </div>
        </main>

        {/* Right Panel (320px) */}
        <aside
          className={`layout-right-panel ${rightPanelOpen ? 'open' : 'closed'}`}
          role="complementary"
        >
          <div className="layout-panel-content">
            {rightPanel}
          </div>
        </aside>
      </div>

      {/* Mobile Overlay */}
      {(sidebarOpen || rightPanelOpen) && (
        <div
          className="layout-overlay"
          onClick={() => {
            setSidebarOpen(false);
            setRightPanelOpen(false);
          }}
        />
      )}
    </div>
  );
};

export default Layout3Column;
