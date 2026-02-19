import React, { useState } from 'react';
import { Eye, Code, Settings, Share2, Download, X } from 'lucide-react';
import './RightPanel.css';

/**
 * Right Panel Component (Preview, Code, Settings)
 * 
 * Features:
 * - Preview toggle
 * - Code viewer
 * - Settings access
 * - Share/Download buttons
 * - Responsive design
 */

export const RightPanel = ({
  preview = null,
  code = null,
  onShare = () => {},
  onDownload = () => {},
  onClose = () => {},
}) => {
  const [activeTab, setActiveTab] = useState('preview'); // 'preview', 'code', 'settings'

  return (
    <div className="right-panel">
      {/* Header */}
      <div className="right-panel-header">
        <div className="right-panel-tabs">
          <button
            className={`right-panel-tab ${activeTab === 'preview' ? 'active' : ''}`}
            onClick={() => setActiveTab('preview')}
            title="Preview"
          >
            <Eye size={16} />
            <span>Preview</span>
          </button>
          <button
            className={`right-panel-tab ${activeTab === 'code' ? 'active' : ''}`}
            onClick={() => setActiveTab('code')}
            title="Code"
          >
            <Code size={16} />
            <span>Code</span>
          </button>
          <button
            className={`right-panel-tab ${activeTab === 'settings' ? 'active' : ''}`}
            onClick={() => setActiveTab('settings')}
            title="Settings"
          >
            <Settings size={16} />
            <span>Settings</span>
          </button>
        </div>
        <button
          className="right-panel-close"
          onClick={onClose}
          title="Close panel"
        >
          <X size={18} />
        </button>
      </div>

      {/* Content */}
      <div className="right-panel-content">
        {/* Preview Tab */}
        {activeTab === 'preview' && (
          <div className="right-panel-tab-content">
            {preview ? (
              <div className="right-panel-preview">
                {preview}
              </div>
            ) : (
              <div className="right-panel-empty">
                <Eye size={32} />
                <p>No preview available</p>
              </div>
            )}
          </div>
        )}

        {/* Code Tab */}
        {activeTab === 'code' && (
          <div className="right-panel-tab-content">
            {code ? (
              <div className="right-panel-code">
                <pre>
                  <code>{code}</code>
                </pre>
              </div>
            ) : (
              <div className="right-panel-empty">
                <Code size={32} />
                <p>No code available</p>
              </div>
            )}
          </div>
        )}

        {/* Settings Tab */}
        {activeTab === 'settings' && (
          <div className="right-panel-tab-content">
            <div className="right-panel-settings">
              <div className="settings-group">
                <h4 className="settings-title">Export</h4>
                <button
                  className="settings-button"
                  onClick={onDownload}
                >
                  <Download size={16} />
                  <span>Download</span>
                </button>
              </div>

              <div className="settings-group">
                <h4 className="settings-title">Share</h4>
                <button
                  className="settings-button"
                  onClick={onShare}
                >
                  <Share2 size={16} />
                  <span>Share</span>
                </button>
              </div>

              <div className="settings-group">
                <h4 className="settings-title">Options</h4>
                <label className="settings-checkbox">
                  <input type="checkbox" defaultChecked />
                  <span>Auto-save</span>
                </label>
                <label className="settings-checkbox">
                  <input type="checkbox" defaultChecked />
                  <span>Live preview</span>
                </label>
                <label className="settings-checkbox">
                  <input type="checkbox" />
                  <span>Dark mode</span>
                </label>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="right-panel-footer">
        <div className="right-panel-actions">
          <button
            className="right-panel-action-button primary"
            onClick={onShare}
            title="Share"
          >
            <Share2 size={16} />
          </button>
          <button
            className="right-panel-action-button"
            onClick={onDownload}
            title="Download"
          >
            <Download size={16} />
          </button>
        </div>
      </div>
    </div>
  );
};

export default RightPanel;
