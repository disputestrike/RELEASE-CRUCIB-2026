import React, { useState, useRef, useEffect } from 'react';
import {
  Eye, Code, Settings, Share2, Download, X, Terminal,
  History, Wrench, FolderTree, ChevronRight, FileOutput,
  Library, BookOpen, LayoutGrid, FileText, Copy, Check,
  ExternalLink, RefreshCw
} from 'lucide-react';
import './RightPanel.css';

/**
 * Right Panel Component — Manus Management UI inspired
 * 
 * Tabs:
 * - Preview (live Sandpack preview or iframe)
 * - Code (file tree + code viewer)
 * - Terminal (output log)
 * - History (build history for current task)
 * - Tools (Exports, Patterns, Prompts, Templates, Docs/Slides/Sheets)
 */

export const RightPanel = ({
  preview = null,
  code = null,
  files = {},
  terminalOutput = [],
  buildHistory = [],
  onShare = () => {},
  onDownload = () => {},
  onClose = () => {},
  onRefreshPreview = () => {},
}) => {
  const [activeTab, setActiveTab] = useState('preview');
  const [selectedFile, setSelectedFile] = useState(null);
  const [copied, setCopied] = useState(false);
  const terminalRef = useRef(null);

  // Auto-scroll terminal
  useEffect(() => {
    if (terminalRef.current && activeTab === 'terminal') {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [terminalOutput, activeTab]);

  const tabs = [
    { id: 'preview', label: 'Preview', icon: Eye },
    { id: 'code', label: 'Code', icon: Code },
    { id: 'terminal', label: 'Terminal', icon: Terminal },
    { id: 'history', label: 'History', icon: History },
    { id: 'tools', label: 'Tools', icon: Wrench },
  ];

  const toolItems = [
    { label: 'Exports', icon: FileOutput, href: '/app/exports' },
    { label: 'Patterns', icon: Library, href: '/app/patterns' },
    { label: 'Prompts', icon: BookOpen, href: '/app/prompts' },
    { label: 'Templates', icon: LayoutGrid, href: '/app/templates' },
    { label: 'Docs / Slides / Sheets', icon: FileText, href: '/app/generate' },
  ];

  const handleCopyCode = () => {
    const text = selectedFile ? files[selectedFile] : (typeof code === 'string' ? code : '');
    if (text) {
      navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const fileList = Object.keys(files || {});

  return (
    <div className="right-panel">
      {/* Header Tabs */}
      <div className="right-panel-header">
        <div className="right-panel-tabs">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              className={`right-panel-tab ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
              title={tab.label}
            >
              <tab.icon size={15} />
              <span>{tab.label}</span>
            </button>
          ))}
        </div>
        <button className="right-panel-close" onClick={onClose} title="Close panel">
          <X size={18} />
        </button>
      </div>

      {/* Content */}
      <div className="right-panel-content">

        {/* Preview Tab */}
        {activeTab === 'preview' && (
          <div className="right-panel-tab-content">
            <div className="preview-toolbar">
              <span className="preview-url-bar">
                <span className="preview-dot green" />
                <span className="preview-url-text">localhost:3000</span>
              </span>
              <button className="preview-action" onClick={onRefreshPreview} title="Refresh">
                <RefreshCw size={14} />
              </button>
              <button className="preview-action" title="Open in new tab">
                <ExternalLink size={14} />
              </button>
            </div>
            {preview ? (
              <div className="right-panel-preview">{preview}</div>
            ) : (
              <div className="right-panel-empty">
                <Eye size={32} />
                <p>Build something to see a preview</p>
                <span className="right-panel-empty-hint">Preview will appear here automatically</span>
              </div>
            )}
          </div>
        )}

        {/* Code Tab */}
        {activeTab === 'code' && (
          <div className="right-panel-tab-content code-tab">
            {/* File Tree */}
            {fileList.length > 0 && (
              <div className="code-file-tree">
                {fileList.map((filename) => (
                  <button
                    key={filename}
                    className={`code-file-item ${selectedFile === filename ? 'active' : ''}`}
                    onClick={() => setSelectedFile(filename)}
                  >
                    <FolderTree size={13} />
                    <span>{filename}</span>
                  </button>
                ))}
              </div>
            )}
            {/* Code Viewer */}
            <div className="code-viewer">
              <div className="code-viewer-header">
                <span className="code-viewer-filename">{selectedFile || 'Code'}</span>
                <button className="code-copy-btn" onClick={handleCopyCode} title="Copy code">
                  {copied ? <Check size={14} /> : <Copy size={14} />}
                </button>
              </div>
              <pre className="code-viewer-content">
                <code>{selectedFile ? files[selectedFile] : (typeof code === 'string' ? code : 'No code generated yet')}</code>
              </pre>
            </div>
          </div>
        )}

        {/* Terminal Tab */}
        {activeTab === 'terminal' && (
          <div className="right-panel-tab-content">
            <div className="terminal-container" ref={terminalRef}>
              {terminalOutput.length > 0 ? (
                terminalOutput.map((line, i) => (
                  <div key={i} className={`terminal-line ${line.type || ''}`}>
                    <span className="terminal-prefix">$</span>
                    <span className="terminal-text">{line.text || line}</span>
                  </div>
                ))
              ) : (
                <div className="right-panel-empty">
                  <Terminal size={32} />
                  <p>No output yet</p>
                  <span className="right-panel-empty-hint">Build output will appear here</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* History Tab */}
        {activeTab === 'history' && (
          <div className="right-panel-tab-content">
            {buildHistory.length > 0 ? (
              <div className="history-list">
                {buildHistory.map((entry, i) => (
                  <div key={i} className="history-item">
                    <div className="history-item-header">
                      <span className={`history-status ${entry.status || 'pending'}`}>
                        {entry.status === 'completed' ? '✓' : entry.status === 'failed' ? '✗' : '●'}
                      </span>
                      <span className="history-title">{entry.title || `Build #${buildHistory.length - i}`}</span>
                    </div>
                    <div className="history-meta">
                      <span>{entry.timestamp || 'Just now'}</span>
                      {entry.duration && <span>· {entry.duration}</span>}
                    </div>
                    {entry.summary && <p className="history-summary">{entry.summary}</p>}
                  </div>
                ))}
              </div>
            ) : (
              <div className="right-panel-empty">
                <History size={32} />
                <p>No build history</p>
                <span className="right-panel-empty-hint">Your build history will appear here</span>
              </div>
            )}
          </div>
        )}

        {/* Tools Tab */}
        {activeTab === 'tools' && (
          <div className="right-panel-tab-content">
            <div className="tools-list">
              {toolItems.map((tool) => (
                <a key={tool.href} href={tool.href} className="tools-item">
                  <tool.icon size={18} className="tools-icon" />
                  <span className="tools-label">{tool.label}</span>
                  <ChevronRight size={14} className="tools-arrow" />
                </a>
              ))}
            </div>
            <div className="tools-section">
              <h4 className="tools-section-title">Quick Actions</h4>
              <div className="tools-actions">
                <button className="tools-action-btn" onClick={onShare}>
                  <Share2 size={16} />
                  <span>Share</span>
                </button>
                <button className="tools-action-btn" onClick={onDownload}>
                  <Download size={16} />
                  <span>Download</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default RightPanel;
