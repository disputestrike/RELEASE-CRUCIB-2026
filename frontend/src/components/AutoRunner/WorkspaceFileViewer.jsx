/**
 * Typed viewer for one workspace file (text / markdown / image / binary) — lazy-loaded body from parent cache.
 */
import React, { Suspense, lazy } from 'react';
import Editor from '@monaco-editor/react';
import { toEditorPath } from '../../workspace/workspaceFileUtils';
import './WorkspaceFileViewer.css';

const ReactMarkdown = lazy(() => import('react-markdown'));

function monacoLanguage(editorPath) {
  if (editorPath.endsWith('.css')) return 'css';
  if (editorPath.endsWith('.json')) return 'json';
  if (editorPath.endsWith('.html') || editorPath.endsWith('.htm')) return 'html';
  if (editorPath.endsWith('.tsx') || editorPath.endsWith('.ts')) return 'typescript';
  if (editorPath.endsWith('.py')) return 'python';
  if (editorPath.endsWith('.md')) return 'markdown';
  if (editorPath.endsWith('.yaml') || editorPath.endsWith('.yml')) return 'yaml';
  return 'javascript';
}

export default function WorkspaceFileViewer({
  activePathPosix,
  entry,
  trace,
  editorColorMode = 'dark',
  onTextChange,
}) {
  const editorPath = toEditorPath(activePathPosix);

  const toolbar = (
    <div className="wfv-toolbar">
      <span className="wfv-path" title={editorPath}>
        {activePathPosix || '—'}
      </span>
      {trace && (trace.agent || trace.step_key) ? (
        <span className="wfv-trace" title={`Step ${trace.step_id || ''} @ ${trace.ts || ''}`}>
          {trace.agent || ''}
          {trace.step_key ? ` · ${trace.step_key}` : ''}
        </span>
      ) : (
        <span className="wfv-trace" />
      )}
    </div>
  );

  if (!activePathPosix) {
    return (
      <div className="wfv-wrap">
        {toolbar}
        <div className="wfv-loading">Select a file from the tree.</div>
      </div>
    );
  }

  if (!entry || entry.status === 'loading' || entry.status === 'idle') {
    return (
      <div className="wfv-wrap">
        {toolbar}
        <div className="wfv-loading">Loading file…</div>
      </div>
    );
  }

  if (entry.status === 'error') {
    return (
      <div className="wfv-wrap">
        {toolbar}
        <div className="wfv-error">{entry.error || 'Could not load file.'}</div>
      </div>
    );
  }

  if (entry.status === 'image' && entry.blobUrl) {
    return (
      <div className="wfv-wrap">
        {toolbar}
        <div className="wfv-body">
          <img className="wfv-img" data-testid="wfv-image" src={entry.blobUrl} alt={activePathPosix} />
        </div>
      </div>
    );
  }

  if (entry.status === 'binary') {
    return (
      <div className="wfv-wrap">
        {toolbar}
        <div className="wfv-binary" data-testid="wfv-binary">
          <p>Binary file — preview not available in the editor.</p>
          {entry.blobUrl ? (
            <p>
              <a href={entry.blobUrl} download={activePathPosix.split('/').pop() || 'file'}>
                Download copy
              </a>
            </p>
          ) : null}
        </div>
      </div>
    );
  }

  if (entry.status === 'markdown') {
    return (
      <div className="wfv-wrap">
        {toolbar}
        <div className="wfv-body wfv-md" data-testid="wfv-markdown">
          <Suspense fallback={<div className="wfv-loading">Rendering…</div>}>
            <ReactMarkdown>{entry.text || ''}</ReactMarkdown>
          </Suspense>
        </div>
      </div>
    );
  }

  return (
    <div className="wfv-wrap">
      {toolbar}
      <div className="wfv-body code-pane-editor" data-testid="wfv-monaco">
        <Editor
          height="100%"
          theme={editorColorMode === 'light' ? 'vs' : 'vs-dark'}
          path={editorPath}
          language={monacoLanguage(editorPath)}
          value={entry.text ?? ''}
          onChange={onTextChange}
          options={{ minimap: { enabled: false }, fontSize: 13, wordWrap: 'on' }}
        />
      </div>
    </div>
  );
}
