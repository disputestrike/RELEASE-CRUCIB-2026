import {
  Database,
  Loader2,
  Layers,
} from 'lucide-react';
import CrucibAIComputer from '../CrucibAIComputer';
import { KanbanBoard } from '../orchestration';
import { normalizeWorkspacePath } from './pathUtils';

/**
 * Pro-only workbench panels extracted from Workspace.jsx (A-01 modularization).
 */
export default function WorkspaceProPanels({
  activePanel,
  projectIdFromUrl,
  token,
  serverDbErr,
  serverDbLoading,
  serverDbSnapshots,
  dbPanelMerge,
  setFiles,
  setActiveFile,
  setActivePanel,
  serverDocsErr,
  serverDocsLoading,
  mergedDocFiles,
  docsSelectedPath,
  setDocsSelectedPath,
  analyticsErr,
  analyticsLoading,
  analyticsData,
  buildHistoryList,
  buildTimelineEvents,
  agentsActivity,
  agentApiStatuses,
  projectSandboxErr,
  projectSandboxLoading,
  projectSandboxLogs,
  files,
  versions,
  buildHistoryLoading,
  isBuilding,
  sandpackFiles,
  projectBuildProgress,
  currentPhase,
  currentJobId,
}) {
  return (
    <>
      {activePanel === 'database' && (
        <div className="flex-1 min-h-0 overflow-y-auto p-4">
          {serverDbErr && projectIdFromUrl && (
            <div className="text-xs mb-3 px-2 py-1.5 rounded-lg" style={{ background: 'rgba(248,113,113,0.12)', color: '#fca5a5' }}>{serverDbErr}</div>
          )}
          {projectIdFromUrl && serverDbLoading && (
            <div className="flex items-center gap-2 text-xs mb-3" style={{ color: 'var(--theme-muted)' }}>
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              Loading schema from project workspace…
            </div>
          )}
          {dbPanelMerge.hasRows ? (
            <div className="space-y-3">
              {serverDbSnapshotsSection(serverDbSnapshots, setFiles, setActiveFile, setActivePanel)}
              {dbPanelMerge.editorOnly.length > 0 && (
                <div className="rounded-xl p-4 border" style={{ background: 'var(--theme-surface2)', borderColor: 'var(--theme-border)' }}>
                  <div className="flex items-center gap-2 mb-3">
                    <div className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--theme-muted)' }}>In editor</div>
                    <span className="text-[10px] px-1.5 py-0.5 rounded font-medium" style={{ background: 'rgba(255,255,255,0.08)', color: 'var(--theme-muted)' }}>local</span>
                  </div>
                  <div className="space-y-2">
                    {dbPanelMerge.editorOnly.map((row) => (
                      <button
                        key={row.displayKey}
                        type="button"
                        onClick={() => { setActiveFile(row.displayKey); setActivePanel('code'); }}
                        className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-xs text-left transition hover:bg-white/5 border"
                        style={{ borderColor: 'var(--theme-border)', color: 'var(--theme-text)' }}
                      >
                        <Database className="w-3.5 h-3.5 shrink-0" style={{ color: '#a78bfa' }} />
                        <span className="truncate">{row.path}</span>
                        <span className="ml-auto shrink-0" style={{ color: 'var(--theme-muted)' }}>{row.content?.split('\n').length || 0}L</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {dbPanelMerge.inferredTables.length > 0 && (
                <div className="rounded-xl p-4 border" style={{ background: 'var(--theme-surface2)', borderColor: 'var(--theme-border)' }}>
                  <div className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: 'var(--theme-muted)' }}>Tables ({dbPanelMerge.inferredTables.length})</div>
                  <div className="space-y-1.5">
                    {dbPanelMerge.inferredTables.map((t) => (
                      <div key={t} className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs" style={{ background: 'rgba(255,255,255,0.03)', color: 'var(--theme-text)' }}>
                        <div className="w-2 h-2 rounded-sm" style={{ background: '#3b82f6' }} />
                        {t}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full gap-3 py-12" style={{ color: 'var(--theme-muted)' }}>
              <Database className="w-8 h-8 opacity-30" />
              <div className="text-center">
                <div className="text-sm font-medium mb-1">No database schema yet</div>
                <div className="text-xs opacity-70 max-w-xs">
                  {projectIdFromUrl ? 'No SQL/schema files in the saved workspace yet. Run a fullstack build or add schema under the project.' : 'Open a saved project or build a fullstack app to see schema files.'}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {activePanel === 'docs' && (
        <div className="flex flex-1 min-h-0 overflow-hidden">
          <div className="w-[38%] min-w-[140px] border-r overflow-y-auto shrink-0" style={{ borderColor: 'var(--theme-border)' }}>
            {serverDocsErr && projectIdFromUrl && (
              <div className="text-[11px] m-2 p-2 rounded-lg" style={{ background: 'rgba(248,113,113,0.12)', color: '#fca5a5' }}>{serverDocsErr}</div>
            )}
            {projectIdFromUrl && serverDocsLoading && (
              <div className="flex items-center gap-2 text-xs p-3" style={{ color: 'var(--theme-muted)' }}>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Loading…
              </div>
            )}
            {mergedDocFiles.length === 0 ? (
              <div className="p-4 text-xs" style={{ color: 'var(--theme-muted)' }}>No Markdown files found (.md / .mdx).</div>
            ) : (
              <div className="p-2 space-y-0.5">
                {mergedDocFiles.map((d) => {
                  const active = normalizeWorkspacePath(d.path) === normalizeWorkspacePath(docsSelectedPath);
                  return (
                    <button
                      key={`${d.source}-${d.path}`}
                      type="button"
                      onClick={() => setDocsSelectedPath(d.path)}
                      className="w-full text-left px-2.5 py-2 rounded-lg text-xs transition truncate"
                      style={{
                        background: active ? 'rgba(255,255,255,0.08)' : 'transparent',
                        color: active ? 'var(--theme-text)' : 'var(--theme-muted)',
                        border: active ? '1px solid var(--theme-border)' : '1px solid transparent',
                      }}
                    >
                      <span className="block truncate">{d.path}</span>
                      <span className="text-[10px] opacity-70">{d.source === 'server' ? 'workspace' : 'editor'}</span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
          <div className="flex-1 min-w-0 overflow-y-auto p-4">
            {mergedDocFiles.length > 0 && (() => {
              const doc = mergedDocFiles.find((d) => normalizeWorkspacePath(d.path) === normalizeWorkspacePath(docsSelectedPath)) || mergedDocFiles[0];
              return (
                <div>
                  <div className="text-xs font-semibold mb-2" style={{ color: 'var(--theme-muted)' }}>{doc.path}</div>
                  <pre className="text-xs whitespace-pre-wrap font-sans leading-relaxed" style={{ color: 'var(--theme-text)' }}>{doc.content || '—'}</pre>
                </div>
              );
            })()}
          </div>
        </div>
      )}

      {activePanel === 'analytics' && (
        <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-3">
          {!token && (
            <div className="text-sm" style={{ color: 'var(--theme-muted)' }}>Sign in to load usage and jobs.</div>
          )}
          {analyticsErr && (
            <div className="text-xs px-2 py-1.5 rounded-lg" style={{ background: 'rgba(248,113,113,0.12)', color: '#fca5a5' }}>{analyticsErr}</div>
          )}
          {token && analyticsLoading && (
            <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--theme-muted)' }}>
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              Loading analytics…
            </div>
          )}
          {token && !analyticsLoading && analyticsData && (
            <>
              {projectIdFromUrl && (
                <div className="rounded-xl p-4 border" style={{ background: 'var(--theme-surface2)', borderColor: 'var(--theme-border)' }}>
                  <div className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: 'var(--theme-muted)' }}>This project</div>
                  <div className="space-y-1 text-xs" style={{ color: 'var(--theme-text)' }}>
                    <div><span style={{ color: 'var(--theme-muted)' }}>Recorded builds</span><span className="ml-2 font-medium">{buildHistoryList.length}</span></div>
                    <div><span style={{ color: 'var(--theme-muted)' }}>Orchestration events (session)</span><span className="ml-2 font-medium">{buildTimelineEvents.length}</span></div>
                    <div>
                      <span style={{ color: 'var(--theme-muted)' }}>Tokens (ledger, this id)</span>
                      <span className="ml-2 font-medium">
                        {(analyticsData.tokens?.by_project && analyticsData.tokens.by_project[projectIdFromUrl] != null)
                          ? Number(analyticsData.tokens.by_project[projectIdFromUrl]).toLocaleString()
                          : '—'}
                      </span>
                    </div>
                  </div>
                </div>
              )}
              <div className="rounded-xl p-4 border" style={{ background: 'var(--theme-surface2)', borderColor: 'var(--theme-border)' }}>
                <div className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: 'var(--theme-muted)' }}>Account usage</div>
                <div className="text-2xl font-bold mb-1" style={{ color: 'var(--theme-text)' }}>
                  {analyticsData.tokens?.total_used != null ? Number(analyticsData.tokens.total_used).toLocaleString() : '—'}
                  <span className="text-xs font-normal ml-2" style={{ color: 'var(--theme-muted)' }}>tokens recorded</span>
                </div>
                {analyticsData.tokens?.credit_balance != null && (
                  <div className="text-xs" style={{ color: 'var(--theme-muted)' }}>
                    Balance: <span className="font-medium" style={{ color: 'var(--theme-text)' }}>{Number(analyticsData.tokens.credit_balance).toLocaleString()}</span> credits
                  </div>
                )}
              </div>
              {Array.isArray(analyticsData.tokens?.daily_trend) && analyticsData.tokens.daily_trend.length > 0 && (
                <div className="rounded-xl p-4 border" style={{ background: 'var(--theme-surface2)', borderColor: 'var(--theme-border)' }}>
                  <div className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: 'var(--theme-muted)' }}>Last {Math.min(14, analyticsData.tokens.daily_trend.length)} days</div>
                  <div className="space-y-1 max-h-40 overflow-y-auto">
                    {analyticsData.tokens.daily_trend.slice(0, 14).map((row) => (
                      <div key={row.date} className="flex justify-between text-xs" style={{ color: 'var(--theme-text)' }}>
                        <span style={{ color: 'var(--theme-muted)' }}>{row.date}</span>
                        <span className="font-mono">{Number(row.tokens || 0).toLocaleString()}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              <div className="rounded-xl p-4 border" style={{ background: 'var(--theme-surface2)', borderColor: 'var(--theme-border)' }}>
                <div className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: 'var(--theme-muted)' }}>Jobs</div>
                {(analyticsData.jobs || []).length === 0 ? (
                  <div className="text-xs" style={{ color: 'var(--theme-muted)' }}>No recent jobs.</div>
                ) : (
                  <div className="space-y-1.5">
                    {(analyticsData.jobs || []).slice(0, 12).map((j) => jobRow(j))}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      )}

      {activePanel === 'agents' && (
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          <div className="rounded-xl p-4 border" style={{ background: 'var(--theme-surface2)', borderColor: 'var(--theme-border)' }}>
            <div className="text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: 'var(--theme-muted)' }}>DAG Orchestration</div>
            <div className="text-xs mt-0.5" style={{ color: 'var(--theme-muted)' }}>237 agents · dependency-aware selection · parallel swarm phases</div>
            <div className="text-xs mt-1" style={{ color: 'var(--theme-muted)' }}>
              {currentJobId ? `Live controller attached to job ${currentJobId}` : 'Waiting for a live orchestrator job.'}
            </div>
          </div>
          {currentJobId && (
            <div className="rounded-xl border overflow-hidden" style={{ borderColor: 'var(--theme-border)', background: 'var(--theme-surface2)' }}>
              <KanbanBoard jobId={currentJobId} />
            </div>
          )}
          {projectIdFromUrl && token && agentApiStatuses.length > 0 && (
            <div className="rounded-xl border overflow-hidden" style={{ borderColor: 'var(--theme-border)' }}>
              <div className="px-3 py-2 text-[10px] font-semibold uppercase tracking-wider border-b" style={{ borderColor: 'var(--theme-border)', color: 'var(--theme-muted)', background: 'rgba(0,0,0,0.12)' }}>
                Live agent_status (GET /api/agents/status/{projectIdFromUrl.slice(0, 8)}…)
              </div>
              <div className="max-h-56 overflow-y-auto">
                {agentApiStatuses.slice(0, 40).map((row, i) => {
                  const name = row.agent_name || row.name || 'Agent';
                  const st = (row.status || 'idle').toLowerCase();
                  const running = st === 'running' || st === 'in_progress';
                  const done = st === 'completed' || st === 'done';
                  return (
                    <div key={`${name}-${i}`} className="flex items-center gap-3 px-3 py-2 border-b last:border-b-0 text-xs" style={{ borderColor: 'var(--theme-border)', background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)' }}>
                      <div className="w-5 h-5 rounded-full flex items-center justify-center shrink-0" style={{
                        background: done ? 'rgba(74,222,128,0.15)' : running ? 'rgba(163,163,163,0.2)' : 'rgba(255,255,255,0.05)',
                      }}>
                        {done ? <span style={{ color: '#4ade80', fontSize: 9 }}>✓</span>
                          : running ? <Loader2 className="w-2.5 h-2.5 animate-spin" style={{ color: '#d4d4d4' }} />
                          : <span style={{ color: 'var(--theme-muted)', fontSize: 9 }}>○</span>}
                      </div>
                      <span className="font-medium truncate min-w-0" style={{ color: 'var(--theme-text)' }}>{name}</span>
                      <span className="ml-auto shrink-0 font-mono text-[10px]" style={{ color: 'var(--theme-muted)' }}>
                        {st}{row.progress != null ? ` · ${Math.round(Number(row.progress))}%` : ''}{row.tokens_used != null ? ` · ${Number(row.tokens_used).toLocaleString()} tok` : ''}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
          {!currentJobId && agentsActivity.length > 0 ? (
            <div className="rounded-xl border overflow-hidden" style={{ borderColor: 'var(--theme-border)' }}>
              {agentsActivity.map((a, i) => (
                <div key={i} className="flex items-center gap-3 px-3 py-2.5 border-b last:border-b-0 text-xs" style={{ borderColor: 'var(--theme-border)', background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)' }}>
                  <div className="w-5 h-5 rounded-full flex items-center justify-center shrink-0" style={{
                    background: a.status === 'done' ? 'rgba(74,222,128,0.15)' : a.status === 'running' ? 'rgba(163,163,163,0.2)' : 'rgba(255,255,255,0.05)',
                  }}>
                    {a.status === 'done' ? <span style={{ color: '#4ade80', fontSize: 9 }}>✓</span>
                      : a.status === 'running' ? <Loader2 className="w-2.5 h-2.5 animate-spin" style={{ color: '#d4d4d4' }} />
                      : <span style={{ color: 'var(--theme-muted)', fontSize: 9 }}>○</span>}
                  </div>
                  <span className="font-medium truncate" style={{ color: a.status === 'done' ? '#86efac' : a.status === 'running' ? '#d4d4d4' : 'var(--theme-muted)' }}>{a.name}</span>
                  <span className="ml-auto shrink-0 opacity-60" style={{ color: 'var(--theme-muted)' }}>{a.phase}</span>
                </div>
              ))}
            </div>
          ) : !currentJobId ? (
            <div className="space-y-1.5">
              {[
                { name: 'Planner', desc: 'Intent parsing, task decomposition', phase: 'Planning', color: '#737373' },
                { name: 'Architect', desc: 'System design, component structure', phase: 'Architecture', color: '#6b7280' },
                { name: 'Frontend', desc: 'UI components, pages, styling', phase: 'Generation', color: '#a3a3a3' },
                { name: 'Backend', desc: 'API routes, services, middleware', phase: 'Generation', color: '#9ca3af' },
                { name: 'Database', desc: 'Schema, migrations, ORM', phase: 'Generation', color: '#a1a1aa' },
                { name: 'Styling', desc: 'Tailwind, CSS, theming', phase: 'Generation', color: '#78716c' },
                { name: 'Logic', desc: 'Business logic, state management', phase: 'Generation', color: '#525252' },
                { name: 'Validator', desc: 'Syntax checking, type safety', phase: 'Validation', color: '#57534e' },
                { name: 'Optimizer', desc: 'Bundle optimization, deployment config', phase: 'Deploy', color: '#44403c' },
              ].map((agent, i) => (
                <div key={i} className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs" style={{ background: 'rgba(255,255,255,0.025)', border: '1px solid var(--theme-border)' }}>
                  <div className="w-2 h-2 rounded-full shrink-0" style={{ background: agent.color }} />
                  <div className="min-w-0">
                    <div className="font-medium" style={{ color: 'var(--theme-text)' }}>{agent.name}</div>
                    <div className="opacity-60 truncate" style={{ color: 'var(--theme-muted)' }}>{agent.desc}</div>
                  </div>
                  <span className="ml-auto shrink-0 px-1.5 py-0.5 rounded text-[10px]" style={{ background: 'rgba(255,255,255,0.06)', color: 'var(--theme-muted)' }}>{agent.phase}</span>
                </div>
              ))}
              <div className="text-center py-3 text-xs" style={{ color: 'var(--theme-muted)' }}>Specialized swarm coverage across frontend, backend, security, data, infra, and verification.</div>
            </div>
          ) : null}
        </div>
      )}

      {activePanel === 'passes' && (
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          <div className="rounded-xl p-4 border" style={{ background: 'var(--theme-surface2)', borderColor: 'var(--theme-border)' }}>
            <div className="text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: 'var(--theme-muted)' }}>Multi-Pass Build System</div>
            <div className="text-xs mt-0.5" style={{ color: 'var(--theme-muted)' }}>6 passes · 51-file TypeScript output · iterative refinement</div>
          </div>
          {projectIdFromUrl && buildHistoryList.length > 0 && (
            <div className="rounded-xl border overflow-hidden" style={{ borderColor: 'var(--theme-border)' }}>
              <div className="px-3 py-2 text-[10px] font-semibold uppercase tracking-wider border-b flex items-center gap-2" style={{ borderColor: 'var(--theme-border)', color: 'var(--theme-muted)', background: 'rgba(0,0,0,0.12)' }}>
                Server build history
                {buildHistoryLoading && <Loader2 className="w-3 h-3 animate-spin" />}
              </div>
              <div className="max-h-48 overflow-y-auto divide-y" style={{ borderColor: 'var(--theme-border)' }}>
                {buildHistoryList.slice(0, 25).map((h, i) => (
                  <div key={i} className="px-3 py-2 text-xs flex flex-wrap gap-2 items-center" style={{ color: 'var(--theme-text)' }}>
                    <span className="font-medium capitalize">{h.status || '—'}</span>
                    {h.quality_score != null && <span style={{ color: 'var(--theme-muted)' }}>Q {h.quality_score}</span>}
                    {h.tokens_used != null && <span style={{ color: 'var(--theme-muted)' }}>{Number(h.tokens_used).toLocaleString()} tok</span>}
                    <span className="ml-auto font-mono text-[10px]" style={{ color: 'var(--theme-muted)' }}>{h.completed_at ? new Date(h.completed_at).toLocaleString() : '—'}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {versions.length > 0 ? (
            <div className="space-y-2">
              {[
                { pass: 'Pass 1', label: 'Static Foundation', desc: '11 config files injected: tsconfig, vite, package.json, docker-compose, CI/CD', color: '#737373' },
                { pass: 'Pass 2', label: 'Architecture', desc: 'System design, shared types, API contracts, folder structure', color: '#6b7280' },
                { pass: 'Pass 3', label: 'Frontend Generation', desc: 'React components, pages, routing, state management', color: '#a3a3a3' },
                { pass: 'Pass 4', label: 'Backend Generation', desc: 'Express routes, middleware, services, DB schema', color: '#525252' },
                { pass: 'Pass 5', label: 'Integration', desc: 'Frontend ↔ backend wiring, shared types, API client', color: '#78716c' },
                { pass: 'Pass 6', label: 'Finalization', desc: 'README, docs, deployment config, optimization', color: '#44403c' },
              ].map((p, i) => (
                <div key={i} className="rounded-xl p-3.5 border" style={{ background: 'rgba(255,255,255,0.02)', borderColor: 'var(--theme-border)' }}>
                  <div className="flex items-center gap-2.5 mb-1.5">
                    <div className="w-2 h-2 rounded-full shrink-0" style={{ background: p.color }} />
                    <span className="text-xs font-semibold" style={{ color: p.color }}>{p.pass}</span>
                    <span className="text-xs font-medium" style={{ color: 'var(--theme-text)' }}>{p.label}</span>
                    <div className="ml-auto flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded-full" style={{ background: 'rgba(74,222,128,0.12)', color: '#86efac' }}>
                      <span>✓</span>
                    </div>
                  </div>
                  <div className="text-xs pl-4.5" style={{ color: 'var(--theme-muted)', paddingLeft: '18px' }}>{p.desc}</div>
                </div>
              ))}
              <div className="rounded-xl p-3.5 border text-center" style={{ borderColor: 'var(--theme-border)', background: 'rgba(74,222,128,0.04)' }}>
                <div className="text-sm font-semibold" style={{ color: '#86efac' }}>Build Complete</div>
                <div className="text-xs mt-0.5" style={{ color: 'var(--theme-muted)' }}>{Object.keys(files).length} files · {versions.length} version{versions.length !== 1 ? 's' : ''} saved</div>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 gap-3" style={{ color: 'var(--theme-muted)' }}>
              <Layers className="w-8 h-8 opacity-30" />
              <div className="text-center">
                <div className="text-sm font-medium mb-1">No local versions yet</div>
                <div className="text-xs opacity-70">Run a build to populate versions, or open a project with server build history above.</div>
              </div>
            </div>
          )}
        </div>
      )}

      {activePanel === 'sandbox' && (
        <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-3">
          <div className="rounded-xl p-4 border" style={{ background: 'var(--theme-surface2)', borderColor: 'var(--theme-border)' }}>
            <div className="text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: 'var(--theme-muted)' }}>Sandbox &amp; Computer</div>
            <div className="text-xs mt-0.5" style={{ color: 'var(--theme-muted)' }}>
              <strong>Logs:</strong> orchestration from <span className="font-mono">GET /projects/{'{id}'}/logs</span>.
              <strong className="ml-1">Computer:</strong> isolated Sandpack surface (CrucibAI Computer) + live build signals — browser execution (Phase B remote VM is host-specific infra).
            </div>
          </div>
          <div className="rounded-xl border p-3 overflow-x-auto" style={{ borderColor: 'var(--theme-border)', background: 'var(--theme-surface2)' }}>
            <div className="text-[10px] font-semibold uppercase tracking-wider mb-2" style={{ color: 'var(--theme-muted)' }}>Computer preview</div>
            <CrucibAIComputer
              files={sandpackFiles}
              isActive={isBuilding}
              thinking={currentPhase || projectBuildProgress?.agent || ''}
              activityText={projectBuildProgress?.status || ''}
              tokensUsed={projectBuildProgress?.tokens_used || 0}
              tokensTotal={50000}
              currentStep={projectBuildProgress?.phase ?? 0}
              totalSteps={7}
              hasBuild={versions.length > 0 || Object.keys(sandpackFiles || {}).length > 0}
            />
          </div>
          {!projectIdFromUrl && (
            <div className="text-xs" style={{ color: 'var(--theme-muted)' }}>Open a saved project to load server logs.</div>
          )}
          {projectIdFromUrl && !token && (
            <div className="text-xs" style={{ color: 'var(--theme-muted)' }}>Sign in to load project logs.</div>
          )}
          {projectSandboxErr && (
            <div className="text-xs px-2 py-1.5 rounded-lg" style={{ background: 'rgba(248,113,113,0.12)', color: '#fca5a5' }}>{projectSandboxErr}</div>
          )}
          {projectIdFromUrl && token && projectSandboxLoading && projectSandboxLogs.length === 0 && (
            <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--theme-muted)' }}>
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              Loading project logs…
            </div>
          )}
          {projectIdFromUrl && token && !projectSandboxLoading && projectSandboxLogs.length === 0 && !projectSandboxErr && (
            <div className="text-xs" style={{ color: 'var(--theme-muted)' }}>No server log lines yet for this project.</div>
          )}
          {projectSandboxLogs.length > 0 && (
            <pre className="text-[11px] font-mono whitespace-pre-wrap p-3 rounded-xl border max-h-[min(320px,45vh)] overflow-y-auto" style={{ background: 'rgba(0,0,0,0.25)', borderColor: 'var(--theme-border)', color: 'var(--theme-text)' }}>
              {projectSandboxLogs.map((line, i) => {
                const ts = line.created_at ? new Date(line.created_at).toISOString().slice(11, 19) : '';
                const lvl = (line.level || 'info').toLowerCase();
                const col = lvl === 'error' ? '#f87171' : lvl === 'success' ? '#86efac' : 'var(--theme-muted)';
                return (
                  <div key={line.id || i} className="mb-1">
                    <span style={{ color: 'var(--theme-muted)' }}>[{ts}]</span>{' '}
                    <span style={{ color: col }}>{line.agent || 'orch'}:</span>{' '}
                    <span>{line.message || '—'}</span>
                  </div>
                );
              })}
            </pre>
          )}
        </div>
      )}
    </>
  );
}

function serverDbSnapshotsSection(serverDbSnapshots, setFiles, setActiveFile, setActivePanel) {
  if (!serverDbSnapshots || serverDbSnapshots.length === 0) return null;
  return (
    <div className="rounded-xl p-4 border" style={{ background: 'var(--theme-surface2)', borderColor: 'var(--theme-border)' }}>
      <div className="flex items-center gap-2 mb-3">
        <div className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--theme-muted)' }}>Project workspace</div>
        <span className="text-[10px] px-1.5 py-0.5 rounded font-medium" style={{ background: 'rgba(59,130,246,0.2)', color: '#93c5fd' }}>server</span>
      </div>
      <div className="space-y-2">
        {serverDbSnapshots.map((row) => (
          <button
            key={row.path}
            type="button"
            onClick={() => {
              const key = row.path.startsWith('/') ? row.path : `/${row.path}`;
              setFiles((prev) => ({ ...prev, [key]: { code: row.content } }));
              setActiveFile(key);
              setActivePanel('code');
            }}
            className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-xs text-left transition hover:bg-white/5 border"
            style={{ borderColor: 'var(--theme-border)', color: 'var(--theme-text)' }}
          >
            <Database className="w-3.5 h-3.5 shrink-0" style={{ color: '#60a5fa' }} />
            <span className="truncate">{row.path}</span>
            <span className="ml-auto shrink-0" style={{ color: 'var(--theme-muted)' }}>{row.content?.split('\n').length || 0}L</span>
          </button>
        ))}
      </div>
    </div>
  );
}

function jobRow(j) {
  const started = j.created_at || j.started_at;
  const doneAt = j.completed_at || j.updated_at;
  let durationStr = '';
  if (started) {
    try {
      const a = new Date(started).getTime();
      const endMs = (j.status === 'complete' && doneAt) ? new Date(doneAt).getTime() : Date.now();
      if (!Number.isNaN(a) && !Number.isNaN(endMs)) {
        const sec = Math.max(0, Math.round((endMs - a) / 1000));
        durationStr = sec < 60 ? `${sec}s` : sec < 3600 ? `${Math.round(sec / 60)}m` : `${(sec / 3600).toFixed(1)}h`;
      }
    } catch {
      /* ignore invalid job timestamps */
    }
  }
  const startedShort = started
    ? (() => {
        try {
          const d = new Date(started);
          return Number.isNaN(d.getTime()) ? '' : d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
        } catch (_) {
          return '';
        }
      })()
    : '';
  return (
    <div key={j.id || j.name} className="flex flex-col gap-0.5 text-xs px-2 py-1.5 rounded-lg" style={{ background: 'rgba(255,255,255,0.03)', color: 'var(--theme-text)' }}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-medium truncate max-w-[200px]">{j.name || j.payload?.prompt?.slice?.(0, 40) || j.id || 'Job'}</span>
        <span className="text-[10px] px-1.5 py-0.5 rounded capitalize" style={{ background: 'rgba(255,255,255,0.08)', color: 'var(--theme-muted)' }}>{j.status || '—'}</span>
        {j.progress != null && <span className="ml-auto font-mono text-[10px]" style={{ color: 'var(--theme-muted)' }}>{Math.round(j.progress)}%</span>}
      </div>
      {(startedShort || durationStr) && (
        <div className="text-[10px] font-mono pl-0.5" style={{ color: 'var(--theme-muted)' }}>
          {startedShort && <span>{startedShort}</span>}
          {durationStr && <span className={startedShort ? 'ml-2' : ''}>Δ {durationStr}{j.status !== 'complete' && j.status !== 'failed' ? ' (running)' : ''}</span>}
        </div>
      )}
    </div>
  );
}
