/** Default Sandpack file set when workspace opens with no project files. */
export const DEFAULT_FILES = {
  '/App.js': {
    code: `import React from 'react';

export default function App() {
  return (
    <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #1e293b 0%, #0f172a 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'Inter, sans-serif' }}>
      <div style={{ textAlign: 'center', padding: '2rem' }}>
        <div style={{ width: 64, height: 64, background: '#3b82f6', borderRadius: 16, display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1.5rem' }}>
          <span style={{ fontSize: 28 }}>⚡</span>
        </div>
        <h1 style={{ fontSize: '2.25rem', fontWeight: 700, color: '#f8fafc', marginBottom: '0.75rem', letterSpacing: '-0.02em' }}>
          Welcome to CrucibAI
        </h1>
        <p style={{ color: '#94a3b8', fontSize: '1.125rem', marginBottom: '2rem' }}>
          Describe what you want to build in the chat
        </p>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, padding: '0.5rem 1rem', color: '#64748b', fontSize: '0.875rem' }}>
          <span>💬</span> Type a prompt to get started
        </div>
      </div>
    </div>
  );
}`,
  },
  '/index.js': {
    code: `import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './styles.css';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);`,
  },
  '/styles.css': {
    code: `/* Tailwind CSS loaded via CDN (see externalResources in Sandpack config) */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}`,
  },
};
