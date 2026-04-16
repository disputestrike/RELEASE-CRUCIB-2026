import { computeSandpackFiles, computeSandpackDeps } from './sandpackFromFiles';
import { DEFAULT_FILES } from '../components/workspace/constants';

describe('computeSandpackFiles (preview pipeline)', () => {
  test('typical Vite workspace: src/App.jsx is included and mapped under /src', () => {
    const files = {
      '/src/App.jsx': { code: 'export default function App() { return <div>Hi</div>; }' },
      '/package.json': { code: JSON.stringify({ name: 'x', dependencies: { react: '^19.0.0' } }) },
    };
    const sp = computeSandpackFiles(files);
    expect(Object.keys(sp).length).toBeGreaterThan(0);
    expect(sp['/src/App.jsx']?.code).toMatch(/Hi/);
  });

  test('synthesizes index when App exists but index missing', () => {
    const files = {
      '/src/App.jsx': { code: 'export default function App() { return null; }' },
    };
    const sp = computeSandpackFiles(files);
    expect(sp['/src/index.js']?.code).toMatch(/createRoot/);
    expect(sp['/src/index.js']?.code).toMatch(/App/);
  });

  test('vite.config.ts is excluded from Sandpack (would break in-browser bundler)', () => {
    const files = {
      '/vite.config.ts': { code: "import { defineConfig } from 'vite'\nexport default defineConfig({})" },
      '/src/App.jsx': { code: 'export default function App() { return null; }' },
    };
    const sp = computeSandpackFiles(files);
    expect(sp['/vite.config.ts']).toBeUndefined();
    expect(sp['/src/App.jsx']).toBeDefined();
  });

  test('backend-only tree still allows preview when merged with DEFAULT_FILES (simulates workspace file merge)', () => {
    const merged = {
      ...DEFAULT_FILES,
      '/backend/main.py': { code: 'def app():\n    pass\n' },
    };
    const sp = computeSandpackFiles(merged);
    expect(Object.keys(sp).length).toBeGreaterThan(0);
    expect(sp['/src/App.js'] || sp['/App.js']).toBeDefined();
  });

  test('express-style server entry is excluded', () => {
    const files = {
      '/server.js': { code: "const express = require('express');\nconst app = express();\napp.listen(3000);" },
      '/src/App.jsx': { code: 'export default function App() { return null; }' },
    };
    const sp = computeSandpackFiles(files);
    expect(sp['/server.js']).toBeUndefined();
    expect(sp['/src/App.jsx']).toBeDefined();
  });
});

describe('computeSandpackDeps', () => {
  test('pins react and react-dom to 18.x when package.json requests 19', () => {
    const files = {
      '/package.json': {
        code: JSON.stringify({
          dependencies: { react: '^19.0.0', 'react-dom': '^19.0.0', axios: '^1.7.0' },
        }),
      },
    };
    const deps = computeSandpackDeps(files);
    expect(deps.react).toBe('^18.2.0');
    expect(deps['react-dom']).toBe('^18.2.0');
    expect(deps.axios).toBe('^1.7.0');
  });

  test('without package.json still supplies react 18 for Sandpack template', () => {
    const deps = computeSandpackDeps({});
    expect(deps.react).toBe('^18.2.0');
    expect(deps['react-dom']).toBe('^18.2.0');
  });
});
