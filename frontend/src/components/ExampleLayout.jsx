import React, { useState } from 'react';
import Layout3Column from './Layout3Column';
import Sidebar from './Sidebar';
import RightPanel from './RightPanel';

/**
 * Example Implementation of 3-Column Layout
 * 
 * This shows how to use the Layout3Column component
 * with Sidebar and RightPanel in a real application.
 */

export const ExampleLayout = () => {
  const [projects] = useState([
    { id: 1, name: 'Website Redesign' },
    { id: 2, name: 'Mobile App' },
    { id: 3, name: 'API Integration' },
  ]);

  const [tasks] = useState([
    { id: 1, name: 'Design Homepage', status: 'completed' },
    { id: 2, name: 'Build Components', status: 'running' },
    { id: 3, name: 'Testing', status: 'pending' },
  ]);

  const [user] = useState({
    name: 'John Doe',
    email: 'john@example.com',
  });

  const handleLogout = () => {
    console.log('Logout clicked');
  };

  const handleShare = () => {
    console.log('Share clicked');
  };

  const handleDownload = () => {
    console.log('Download clicked');
  };

  const handleClose = () => {
    console.log('Close panel clicked');
  };

  // Sidebar content
  const sidebarContent = (
    <Sidebar
      user={user}
      onLogout={handleLogout}
      projects={projects}
      tasks={tasks}
    />
  );

  // Main content
  const mainContent = (
    <div className="main-content-example">
      <div className="main-header">
        <h1>Welcome to CrucibAI</h1>
        <p>Select a project or task from the sidebar to get started.</p>
      </div>

      <div className="main-body">
        <div className="content-card">
          <h2>Getting Started</h2>
          <p>
            This is the main content area. It expands to fill available space
            and can contain any content you need.
          </p>
          <ul>
            <li>Create new projects</li>
            <li>View your tasks</li>
            <li>Collaborate with team</li>
            <li>Deploy to production</li>
          </ul>
        </div>

        <div className="content-card">
          <h2>Features</h2>
          <ul>
            <li>115 AI agents</li>
            <li>Real-time preview</li>
            <li>Code generation</li>
            <li>One-click deployment</li>
          </ul>
        </div>
      </div>
    </div>
  );

  // Right panel content
  const previewContent = (
    <div className="preview-example">
      <h3>Live Preview</h3>
      <p>Your project preview appears here in real-time.</p>
    </div>
  );

  const codeContent = `// Generated code example
function App() {
  return (
    <div className="app">
      <h1>Hello World</h1>
    </div>
  );
}`;

  const rightPanelContent = (
    <RightPanel
      preview={previewContent}
      code={codeContent}
      onShare={handleShare}
      onDownload={handleDownload}
      onClose={handleClose}
    />
  );

  return (
    <Layout3Column
      sidebar={sidebarContent}
      main={mainContent}
      rightPanel={rightPanelContent}
    />
  );
};

export default ExampleLayout;

// Styles for example
const exampleStyles = `
.main-content-example {
  display: flex;
  flex-direction: column;
  gap: 24px;
  max-width: 1000px;
}

.main-header {
  padding-bottom: 24px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
}

.main-header h1 {
  margin: 0 0 8px 0;
  font-size: 32px;
  color: #1A1A1A;
}

.main-header p {
  margin: 0;
  font-size: 16px;
  color: #808080;
}

.main-body {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 16px;
}

.content-card {
  padding: 20px;
  background: #FFFFFF;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 12px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.content-card h2 {
  margin: 0 0 12px 0;
  font-size: 18px;
  color: #1A1A1A;
}

.content-card p {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: #808080;
}

.content-card ul {
  margin: 0;
  padding-left: 20px;
  list-style: disc;
}

.content-card li {
  margin: 4px 0;
  font-size: 14px;
  color: #808080;
}

.preview-example {
  padding: 24px;
  text-align: center;
  color: #999999;
}

.preview-example h3 {
  margin: 0 0 12px 0;
  font-size: 16px;
  color: #1A1A1A;
}

.preview-example p {
  margin: 0;
  font-size: 14px;
}
`;
