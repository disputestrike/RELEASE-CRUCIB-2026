/**
 * Editor `files` map → Sandpack files + deps (aligned with Workspace.jsx).
 */

function buildSandpackFilesMap(files) {
  const EXCLUDED =
    /\.(test|spec)\.[jt]sx?$|Dockerfile|docker-compose|\.md$|\.sh$|\.ya?ml$|\.env|\.gitignore|server\.(js|ts)$|express|mongoose|vite\.config\.|craco\.config|tailwind\.config|postcss\.config|jest\.config|setupTests|serviceWorker|reportWebVitals/i;
  const ALLOWED = /\.(jsx?|tsx?|css|html|json)$/i;
  const BACKEND_CODE = /require\(['"]express['"]\)|require\(['"]mongoose['"]\)|require\(['"]mongodb['"]\)|from ['"]express['"]|from ['"]mongoose['"]|app\.listen\(|mongoose\.connect\(/;

  const filtered = Object.entries(files || {}).filter(([path, f]) => {
    if (!ALLOWED.test(path) || EXCLUDED.test(path)) return false;
    if (f?.code && BACKEND_CODE.test(f.code)) return false;
    return true;
  });

  const ROOT_TO_SRC = {
    '/App.js': '/src/App.js',
    '/App.jsx': '/src/App.jsx',
    '/App.ts': '/src/App.js',
    '/App.tsx': '/src/App.jsx',
    '/index.js': '/src/index.js',
    '/index.jsx': '/src/index.jsx',
    '/index.ts': '/src/index.js',
    '/index.tsx': '/src/index.jsx',
    '/styles.css': '/src/styles.css',
  };

  const result = Object.fromEntries(
    filtered.map(([path, f]) => {
      const normalizedPath = path.startsWith('/') ? path : `/${path}`;
      let sandpackPath = ROOT_TO_SRC[normalizedPath] || normalizedPath;
      sandpackPath = sandpackPath.replace(/\.tsx$/, '.jsx').replace(/(?<!\.d)\.ts$/, '.js');
      let code = f?.code || '';
      code = code.replace(/^import\s+type\s+.*?;?$/gm, '');
      code = code.replace(/:\s*React\.FC<[^>]*>/g, '');
      code = code.replace(/:\s*[A-Z][A-Za-z]*(<[^>]*>)?\s*=/g, ' =');
      code = code.replace(/as\s+[A-Z][A-Za-z0-9_<>\[\]]*\b/g, '');
      code = code
        .replace(/import\s*\{\s*BrowserRouter(\s*,\s*|\s+as\s+\w+\s*,?\s*)/g, 'import { MemoryRouter$1')
        .replace(/import\s*\{\s*([^}]*),?\s*BrowserRouter\s*,?\s*([^}]*)\}/g, (_, a, b) =>
          `import { ${[a, b].filter(Boolean).join(', ')}, MemoryRouter }`)
        .replace(/<BrowserRouter>/g, '<MemoryRouter>')
        .replace(/<\/BrowserRouter>/g, '</MemoryRouter>')
        .replace(/BrowserRouter\b/g, 'MemoryRouter');
      if (sandpackPath === '/src/index.js' || sandpackPath === '/src/index.jsx') {
        code = code.replace(/from\s+['"]\.\/App['"]/g, "from './App'");
      }
      if (
        (sandpackPath.includes('styles.css') || sandpackPath.includes('index.css') || sandpackPath.includes('App.css')) &&
        !code.includes('tailwindcss') &&
        !code.includes('tailwind')
      ) {
        code = `@import url('https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css');\n\n${code}`;
      }
      return [sandpackPath, { ...f, code }];
    }),
  );

  const hasAppJsx = !!(result['/src/App.jsx'] || result['/App.jsx']);
  const hasAppJs = !!(result['/src/App.js'] || result['/App.js']);
  const hasApp = hasAppJsx || hasAppJs;
  const existingIndex = result['/src/index.js']?.code || result['/src/index.jsx']?.code || '';
  const indexValid =
    existingIndex.includes("getElementById('root')") && (existingIndex.includes('createRoot') || existingIndex.includes('render('));
  if (Object.keys(result).length > 0 && hasApp && (!result['/src/index.js'] && !result['/src/index.jsx'] || !indexValid)) {
    const appImport = hasAppJsx ? "import App from './App.jsx';" : "import App from './App.js';";
    result['/src/index.js'] = {
      code: `import React from 'react';
import ReactDOM from 'react-dom/client';
${appImport}
${result['/src/styles.css'] || result['/src/App.css'] ? "import './styles.css';" : ''}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);`,
    };
  }
  let isFallback = false;
  if (Object.keys(result).length > 0 && !hasApp && !result['/src/index.js']) {
    const firstJsx = Object.keys(result).find((k) => k.endsWith('.jsx') || k.endsWith('.js'));
    if (firstJsx) {
      isFallback = true;
      const compName = firstJsx.split('/').pop().replace(/\.(jsx?|tsx?)$/, '');
      result['/src/index.js'] = {
        code: `import React from 'react';
import ReactDOM from 'react-dom/client';
import ${compName} from '${firstJsx.replace('/src/', './')}';
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<${compName} />);`,
      };
    }
  }
  return { result, isFallback };
}

/** @returns {{ sandpackFiles: Record<string, { code?: string }>, isFallback: boolean }} */
export function computeSandpackFilesWithMeta(files) {
  const { result, isFallback } = buildSandpackFilesMap(files);
  return { sandpackFiles: result, isFallback };
}

export function computeSandpackFiles(files) {
  return buildSandpackFilesMap(files).result;
}

export function computeSandpackDeps(files) {
  const base = {
    axios: '^1.6.2',
    'react-router-dom': '^6.8.0',
    'lucide-react': '^0.263.1',
    'date-fns': '^2.30.0',
    recharts: '^2.8.0',
    'framer-motion': '^10.16.4',
    clsx: '^2.0.0',
    'class-variance-authority': '^0.7.0',
    'tailwind-merge': '^2.0.0',
    '@radix-ui/react-dialog': '^1.0.5',
    '@radix-ui/react-dropdown-menu': '^2.0.6',
    '@radix-ui/react-select': '^2.0.0',
    '@radix-ui/react-tabs': '^1.0.4',
    '@radix-ui/react-tooltip': '^1.0.7',
    zustand: '^4.4.1',
    'react-hook-form': '^7.47.0',
    zod: '^3.22.4',
  };
  try {
    const pkgJson = files?.['/package.json']?.code || files?.['package.json']?.code;
    if (pkgJson) {
      const pkg = JSON.parse(pkgJson);
      const merged = { ...base, ...(pkg.dependencies || {}), ...(pkg.devDependencies || {}) };
      // Sandpack React template expects React 18; pin to avoid blank preview when package.json asks for 19.
      merged.react = '^18.2.0';
      merged['react-dom'] = '^18.2.0';
      return merged;
    }
  } catch (_) {
    /* ignore */
  }
  return { ...base, react: '^18.2.0', 'react-dom': '^18.2.0' };
}
