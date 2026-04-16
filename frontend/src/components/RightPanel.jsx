/**
 * RightPanel — Monaco editor + live preview + device toggle
 * Wired to real /api/jobs/{id}/workspace/files endpoint.
 * No placeholders. Monaco = VS Code engine.
 */
import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { API_BASE as API } from '../apiBase';
import { SandpackProvider, SandpackPreview } from '@codesandbox/sandpack-react';

// Lazy-load Monaco to avoid bundle bloat
let MonacoEditor = null;
const loadMonaco = async () => {
  if (MonacoEditor) return MonacoEditor;
  try {
    const mod = await import('@monaco-editor/react');
    MonacoEditor = mod.default;
    return MonacoEditor;
  } catch {
    return null;
  }
};

const LANG_MAP = {
  js: 'javascript', jsx: 'javascript', ts: 'typescript', tsx: 'typescript',
  py: 'python', json: 'json', css: 'css', html: 'html', md: 'markdown',
  sql: 'sql', yaml: 'yaml', yml: 'yaml', sh: 'shell', txt: 'plaintext',
};

function getLanguage(path) {
  const ext = (path || '').split('.').pop()?.toLowerCase();
  return LANG_MAP[ext] || 'plaintext';
}

function FileTree({ files, activeFile, onSelect }) {
  // Group by directory
  const tree = {};
  files.forEach(f => {
    const parts = f.path.split('/');
    const dir = parts.length > 1 ? parts.slice(0,-1).join('/') : '';
    if (!tree[dir]) tree[dir] = [];
    tree[dir].push(f);
  });

  const dirs = Object.keys(tree).sort();
  return (
    <div style={{ overflow:'auto', height:'100%', background:'#fafaf8' }}>
      {dirs.map(dir => (
        <div key={dir}>
          {dir && (
            <div style={{ padding:'6px 12px 2px', fontSize:10, fontWeight:700,
              textTransform:'uppercase', letterSpacing:'0.06em', color:'#9ca3af' }}>
              {dir}/
            </div>
          )}
          {tree[dir].map(f => {
            const name = f.path.split('/').pop();
            const isActive = f.path === activeFile;
            return (
              <button key={f.path} onClick={() => onSelect(f.path)}
                style={{ width:'100%', textAlign:'left',
                  padding:'5px 12px 5px ' + (dir ? '20px' : '12px'),
                  background: isActive ? '#ecfdf5' : 'transparent',
                  border:'none', cursor:'pointer', display:'flex',
                  alignItems:'center', gap:6, fontSize:12,
                  color: isActive ? '#065f46' : '#374151',
                  fontWeight: isActive ? 500 : 400 }}>
                <span style={{ fontSize:11 }}>📄</span>
                <span style={{ flex:1, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>
                  {name}
                </span>
                <span style={{ fontSize:10, color:'#d1d5db' }}>
                  {(f.size/1024).toFixed(1)}k
                </span>
              </button>
            );
          })}
        </div>
      ))}
      {files.length === 0 && (
        <div style={{ padding:16, fontSize:12, color:'#9ca3af', textAlign:'center' }}>
          No files yet
        </div>
      )}
    </div>
  );
}

export default function RightPanel({
  jobId,
  token,
  steps,
  isRunning,
  previewUrl,
  sandpackFiles,
  simulationRecommendation,
  onApplySimulationRecommendation,
  onRejectSimulationRecommendation,
}) {
  const [tab, setTab] = useState('preview');
  const [files, setFiles] = useState([]);
  const [activeFile, setActiveFile] = useState(null);
  const [fileContent, setFileContent] = useState({});
  const [device, setDevice] = useState('desktop');
  const [monacoLoaded, setMonacoLoaded] = useState(false);
  const [MonacoComp, setMonacoComp] = useState(null);

  // Load Monaco lazily
  useEffect(() => {
    loadMonaco().then(m => { if (m) { setMonacoComp(() => m); setMonacoLoaded(true); }});
  }, []);

  // Load workspace files
  const loadFiles = useCallback(async () => {
    if (!jobId || !token) return;
    try {
      const res = await axios.get(`${API}/jobs/${jobId}/workspace/files`,
        { headers: { Authorization: `Bearer ${token}` } });
      setFiles(res.data?.files || []);
    } catch {
      setFiles([]);
    }
  }, [jobId, token]);

  useEffect(() => { loadFiles(); }, [loadFiles]);
  useEffect(() => { if (!isRunning && jobId) loadFiles(); }, [isRunning, jobId, loadFiles]);

  // Load file content
  const selectFile = useCallback(async (path) => {
    setActiveFile(path);
    if (fileContent[path] !== undefined) return;
    try {
      const res = await axios.get(`${API}/jobs/${jobId}/workspace/file`,
        { headers: { Authorization: `Bearer ${token}` }, params: { path } });
      setFileContent(prev => ({ ...prev, [path]: res.data?.content || '' }));
    } catch {
      setFileContent(prev => ({ ...prev, [path]: '// Could not load file' }));
    }
  }, [jobId, token, fileContent]);

  const tabs = ['preview', 'code', 'files', 'publish', 'proof'];

  return (
    <div data-testid="right-panel-root" style={{ height:'100%', display:'flex', flexDirection:'column', background:'#fff' }}>
      {/* Tab bar */}
      <div style={{ display:'flex', alignItems:'center', borderBottom:'1px solid #e5e7eb',
        background:'#f9fafb', flexShrink:0 }}>
        {tabs.map(t => (
          <button key={t} onClick={() => setTab(t)}
            style={{ padding:'10px 16px', fontSize:13, border:'none', background:'transparent',
              cursor:'pointer', borderBottom: tab === t ? '2px solid #10b981' : '2px solid transparent',
              color: tab === t ? '#065f46' : '#6b7280', fontWeight: tab === t ? 500 : 400,
              marginBottom:-1, transition:'all 0.15s' }}>
            {t === 'preview'
              ? '👁 Preview'
              : t === 'code'
                ? '📄 Code'
                : t === 'files'
                  ? '🗂 Files'
                  : t === 'publish'
                    ? '🚀 Publish'
                    : '✓ Proof'}
          </button>
        ))}
        <div style={{ flex:1 }} />
        {/* Device toggle — preview only */}
        {tab === 'preview' && (
          <div style={{ display:'flex', gap:2, marginRight:12 }}>
            {['desktop','mobile'].map(d => (
              <button key={d} onClick={() => setDevice(d)}
                style={{ padding:'4px 8px', borderRadius:6, border:'1px solid',
                  borderColor: device === d ? '#10b981' : '#e5e7eb',
                  background: device === d ? '#ecfdf5' : 'transparent',
                  fontSize:12, color: device === d ? '#065f46' : '#9ca3af',
                  cursor:'pointer' }}>
                {d === 'desktop' ? '🖥' : '📱'}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Content */}
      <div style={{ flex:1, overflow:'hidden', display:'flex', flexDirection:'column' }}>

        {/* Preview */}
        {tab === 'preview' && (
          <div style={{ flex:1, display:'flex', flexDirection:'column', overflow:'hidden' }}>
            {simulationRecommendation && (
              <div style={{ margin:'10px 12px 0', padding:'10px 12px', borderRadius:10, border:'1px solid #a7f3d0', background:'#ecfdf5' }}>
                <div style={{ fontSize:12, color:'#065f46', fontWeight:700, marginBottom:4 }}>
                  Simulation Result
                </div>
                <div style={{ fontSize:12, color:'#064e3b' }}>
                  Recommended: {simulationRecommendation.recommended_action} (confidence {Math.round((simulationRecommendation.confidence || 0) * 100)}%)
                </div>
                {Array.isArray(simulationRecommendation.tradeoffs) && simulationRecommendation.tradeoffs.length > 0 && (
                  <div style={{ fontSize:11, color:'#047857', marginTop:6 }}>
                    {simulationRecommendation.tradeoffs.slice(0, 3).map((t, i) => (
                      <div key={`sim-tradeoff-${i}`}>• {t}</div>
                    ))}
                  </div>
                )}
                <div style={{ marginTop:8, display:'flex', gap:8 }}>
                  <button
                    type="button"
                    onClick={onApplySimulationRecommendation}
                    style={{ border:'1px solid #059669', background:'#059669', color:'#fff', borderRadius:6, fontSize:12, padding:'4px 10px', cursor:'pointer' }}
                  >
                    Apply Recommendation
                  </button>
                  <button
                    type="button"
                    onClick={onRejectSimulationRecommendation}
                    style={{ border:'1px solid #d1d5db', background:'#fff', color:'#374151', borderRadius:6, fontSize:12, padding:'4px 10px', cursor:'pointer' }}
                  >
                    Reject
                  </button>
                </div>
              </div>
            )}
            {/* URL bar */}
            <div style={{ padding:'6px 12px', background:'#f3f4f6', borderBottom:'1px solid #e5e7eb',
              display:'flex', alignItems:'center', gap:8, flexShrink:0 }}>
              <button onClick={loadFiles} style={{ background:'none', border:'none',
                color:'#9ca3af', cursor:'pointer', fontSize:14 }} title="Refresh">↻</button>
              <div style={{ flex:1, background:'#fff', border:'1px solid #e5e7eb',
                borderRadius:6, padding:'4px 10px', fontSize:11, color:'#6b7280',
                overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>
                {previewUrl ? previewUrl.replace(/^https?:\/\//, '') : 'Building…'}
              </div>
              {previewUrl && (
                <button onClick={() => window.open(previewUrl, '_blank')}
                  style={{ background:'none', border:'none', color:'#10b981',
                    cursor:'pointer', fontSize:14 }} title="Open in new tab">↗</button>
              )}
            </div>

            {/* Preview frame */}
            <div style={{ flex:1, overflow:'hidden', background:'#f3f4f6',
              padding: device === 'mobile' ? '16px' : '0',
              display:'flex', justifyContent:'center' }}>
              <div style={{
                width: device === 'mobile' ? 390 : '100%',
                height:'100%', background:'#fff',
                boxShadow: device === 'mobile' ? '0 4px 20px rgba(0,0,0,0.15)' : 'none',
                borderRadius: device === 'mobile' ? 12 : 0,
                overflow:'hidden', flexShrink:0,
              }}>
                {previewUrl ? (
                  <iframe src={previewUrl} title="Live Preview"
                    style={{ width:'100%', height:'100%', border:'none' }}
                    sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals" />
                ) : Object.keys(sandpackFiles || {}).length > 0 ? (
                  <SandpackProvider files={sandpackFiles} template="react"
                    theme="light" options={{ autoReload:true, recompileDelay:500 }}>
                    <SandpackPreview style={{ height:'100%' }} />
                  </SandpackProvider>
                ) : (
                  <div style={{ height:'100%', display:'flex', flexDirection:'column',
                    alignItems:'center', justifyContent:'center', color:'#9ca3af', gap:12, padding:32 }}>
                    {/* Manus-style skeleton */}
                    <div style={{ width:120, height:90, border:'2px solid #e5e7eb',
                      borderRadius:8, padding:10, display:'flex', flexDirection:'column', gap:6 }}>
                      <div style={{ height:8, background:'#e5e7eb', borderRadius:4, width:'100%' }} />
                      <div style={{ display:'flex', gap:4 }}>
                        <div style={{ height:8, background:'#e5e7eb', borderRadius:4, width:'40%' }} />
                        <div style={{ height:8, background:'#e5e7eb', borderRadius:4, width:'55%' }} />
                      </div>
                      <div style={{ height:8, background:'#e5e7eb', borderRadius:4, width:'70%' }} />
                      <div style={{ display:'flex', gap:4 }}>
                        <div style={{ height:8, background:'#e5e7eb', borderRadius:4, width:'30%' }} />
                        <div style={{ height:8, background:'#e5e7eb', borderRadius:4, width:'60%' }} />
                      </div>
                    </div>
                    <div style={{ fontSize:13, textAlign:'center', lineHeight:1.5 }}>
                      {isRunning ? 'Building your app…\nPreview appears as code generates' : 'Start a build to see preview'}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Code — Monaco editor + file tree */}
        {tab === 'code' && (
          <div style={{ flex:1, display:'flex', overflow:'hidden' }}>
            {/* File tree */}
            <div style={{ width:220, borderRight:'1px solid #e5e7eb', overflow:'hidden',
              display:'flex', flexDirection:'column' }}>
              <div style={{ padding:'8px 12px 4px', fontSize:11, fontWeight:700,
                textTransform:'uppercase', letterSpacing:'0.06em', color:'#9ca3af',
                borderBottom:'1px solid #f3f4f6', flexShrink:0,
                display:'flex', justifyContent:'space-between', alignItems:'center' }}>
                <span>Files ({files.length})</span>
                <button type="button" data-testid="workspace-files-refresh" onClick={loadFiles} style={{ background:'none', border:'none',
                  color:'#9ca3af', cursor:'pointer', fontSize:12 }}>↻</button>
              </div>
              <div style={{ flex:1, overflow:'auto' }}>
                <FileTree files={files} activeFile={activeFile} onSelect={selectFile} />
              </div>
              {jobId && (
                <div style={{ padding:'6px 12px', borderTop:'1px solid #e5e7eb', flexShrink:0 }}>
                  <a href={`${API}/jobs/${jobId}/workspace/download`} download
                    style={{ fontSize:11, color:'#10b981', textDecoration:'none',
                      display:'flex', alignItems:'center', gap:4 }}>
                    📥 Download ZIP
                  </a>
                </div>
              )}
            </div>

            {/* Editor */}
            <div style={{ flex:1, overflow:'hidden' }}>
              {activeFile ? (
                monacoLoaded && MonacoComp ? (
                  <MonacoComp
                    height="100%"
                    language={getLanguage(activeFile)}
                    value={fileContent[activeFile] || '// Loading…'}
                    theme="light"
                    options={{
                      minimap: { enabled: false },
                      fontSize: 13,
                      fontFamily: "'Fira Code', 'Cascadia Code', monospace",
                      scrollBeyondLastLine: false,
                      lineNumbers: 'on',
                      readOnly: true,
                      wordWrap: 'on',
                      padding: { top: 12 },
                    }}
                  />
                ) : (
                  <pre style={{ margin:0, padding:16, fontSize:12, overflow:'auto',
                    height:'100%', fontFamily:"'Fira Code', monospace",
                    color:'#374151', lineHeight:1.6, whiteSpace:'pre-wrap',
                    background:'#fafaf8' }}>
                    {fileContent[activeFile] || '// Loading…'}
                  </pre>
                )
              ) : (
                <div style={{ height:'100%', display:'flex', alignItems:'center',
                  justifyContent:'center', color:'#9ca3af', fontSize:13 }}>
                  {files.length > 0 ? '← Select a file' : isRunning ? 'Files generating…' : 'No files yet'}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Files — dedicated workspace file browser mode */}
        {tab === 'files' && (
          <div style={{ flex:1, display:'flex', flexDirection:'column', overflow:'hidden' }}>
            <div style={{ padding:'10px 12px', borderBottom:'1px solid #e5e7eb',
              display:'flex', alignItems:'center', justifyContent:'space-between' }}>
              <div style={{ fontSize:12, color:'#374151', fontWeight:600 }}>
                Workspace files ({files.length})
              </div>
              <div style={{ display:'flex', gap:8 }}>
                <button type="button" onClick={loadFiles} style={{
                  border:'1px solid #d1d5db', background:'#fff', color:'#374151',
                  borderRadius:6, fontSize:12, padding:'4px 8px', cursor:'pointer'
                }}>
                  Refresh
                </button>
                {jobId && (
                  <a href={`${API}/jobs/${jobId}/workspace/download`} download style={{
                    border:'1px solid #10b981', background:'#ecfdf5', color:'#065f46',
                    borderRadius:6, fontSize:12, padding:'4px 8px', textDecoration:'none'
                  }}>
                    Download ZIP
                  </a>
                )}
              </div>
            </div>
            <div style={{ flex:1, overflow:'hidden' }}>
              <FileTree files={files} activeFile={activeFile} onSelect={selectFile} />
            </div>
          </div>
        )}

        {/* Publish — dedicated publish/readiness mode */}
        {tab === 'publish' && (
          <div style={{ flex:1, overflow:'auto', padding:16, display:'flex', flexDirection:'column', gap:12 }}>
            <div style={{ fontSize:13, color:'#374151', fontWeight:600 }}>Publish readiness</div>
            <div style={{ fontSize:12, color:'#6b7280', lineHeight:1.6 }}>
              Use this mode to open the latest preview, export workspace artifacts, and hand off a deploy-ready bundle.
            </div>

            <div style={{ border:'1px solid #e5e7eb', borderRadius:10, padding:12, background:'#fafaf8' }}>
              <div style={{ fontSize:11, color:'#9ca3af', textTransform:'uppercase', letterSpacing:'0.05em', marginBottom:6 }}>
                Preview URL
              </div>
              <div style={{ fontSize:12, color:'#374151', wordBreak:'break-all' }}>
                {previewUrl || 'No preview URL yet. Run a build to generate one.'}
              </div>
              {previewUrl && (
                <div style={{ marginTop:10 }}>
                  <button type="button" onClick={() => window.open(previewUrl, '_blank')} style={{
                    border:'1px solid #10b981', background:'#10b981', color:'#fff',
                    borderRadius:6, fontSize:12, padding:'6px 10px', cursor:'pointer'
                  }}>
                    Open Live Preview
                  </button>
                </div>
              )}
            </div>

            {jobId && (
              <div style={{ border:'1px solid #e5e7eb', borderRadius:10, padding:12, background:'#fff' }}>
                <div style={{ fontSize:11, color:'#9ca3af', textTransform:'uppercase', letterSpacing:'0.05em', marginBottom:6 }}>
                  Export Bundle
                </div>
                <a href={`${API}/jobs/${jobId}/workspace/download`} download style={{
                  display:'inline-block', border:'1px solid #d1d5db', background:'#fff', color:'#374151',
                  borderRadius:6, fontSize:12, padding:'6px 10px', textDecoration:'none'
                }}>
                  Download Workspace ZIP
                </a>
              </div>
            )}
          </div>
        )}

        {/* Proof */}
        {tab === 'proof' && (
          <div style={{ flex:1, overflow:'auto', padding:16 }}>
            <div style={{ fontSize:13, color:'#374151' }}>
              {steps?.filter(s => s.status === 'completed').length || 0} steps complete
              {steps?.some(s => s.status === 'failed') && (
                <span style={{ color:'#ef4444', marginLeft:12 }}>
                  {steps.filter(s => s.status === 'failed').length} failed
                </span>
              )}
            </div>
            <div style={{ marginTop:12, display:'flex', flexDirection:'column', gap:6 }}>
              {(steps || []).map(s => (
                <div key={s.id} style={{ display:'flex', alignItems:'center', gap:8,
                  padding:'6px 10px', borderRadius:6, fontSize:12,
                  background: s.status === 'completed' ? '#f0fdf4' :
                               s.status === 'failed' ? '#fef2f2' : '#f9fafb',
                  border: '1px solid ' + (s.status === 'completed' ? '#bbf7d0' :
                                          s.status === 'failed' ? '#fecaca' : '#e5e7eb') }}>
                  <span>{s.status === 'completed' ? '✓' : s.status === 'failed' ? '✗' : '⏳'}</span>
                  <span style={{ flex:1, color:'#374151' }}>{s.agent_name || s.step_key}</span>
                  <span style={{ color:'#9ca3af', fontSize:10 }}>{s.phase}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
