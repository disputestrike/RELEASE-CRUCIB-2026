/**
 * Backend Integration — maps frontend concepts to CrucibAI's real backend
 * 
 * Our backend has:
 * - 245 agents in AGENT_DAG (backend/agent_dag.py)
 * - 37 workflows (backend/workflows.py)
 * - SSE stream at /api/jobs/{id}/stream
 * - WebSocket at /ws/events?jobId={id}  (adapter layer)
 * - REST at /api/build, /api/builds/{id}/interrupt, etc.
 * 
 * This file is the single source of truth for all API calls.
 */

import { workspaceZipQuery } from './workspaceZip';

const BASE = (typeof process !== 'undefined' && process.env?.REACT_APP_API_URL) || '';

// ── Auth helper ───────────────────────────────────────────────────────────────
function authHeaders(token) {
  return token ? { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' };
}

// ── Build lifecycle ───────────────────────────────────────────────────────────

export async function startBuild({ prompt, attachments = [], mode = 'auto', thinkingEffort = 'medium', token }) {
  // Try adapter endpoint first, fall back to orchestrator
  try {
    const res = await fetch(`${BASE}/api/build`, {
      method: 'POST',
      headers: authHeaders(token),
      body: JSON.stringify({ prompt, attachments, mode, thinkingEffort }),
    });
    if (res.ok) return res.json();
  } catch {}

  // Fallback to our original orchestrator
  const planRes = await fetch(`${BASE}/api/orchestrator/plan`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify({ goal: prompt, mode }),
  });
  const plan = await planRes.json();
  const jobId = plan.job_id;

  await fetch(`${BASE}/api/orchestrator/run-auto`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify({ job_id: jobId }),
  });

  return { jobId, status: 'running', createdAt: new Date().toISOString() };
}

export async function steerBuild({ jobId, instruction, kind = 'custom_instruction', token }) {
  const res = await fetch(`${BASE}/api/jobs/${jobId}/steer`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify({ action: 'interrupt', kind, instruction, resume: true }),
  });
  return res.ok ? res.json() : { accepted: false, message: 'Steer failed' };
}

export async function getJobStatus(jobId, token) {
  const res = await fetch(`${BASE}/api/jobs/${jobId}`, { headers: authHeaders(token) });
  return res.ok ? res.json() : null;
}

export async function getJobSteps(jobId, token) {
  const res = await fetch(`${BASE}/api/jobs/${jobId}/history`, { headers: authHeaders(token) });
  return res.ok ? (await res.json()).steps || [] : [];
}

export async function getJobProof(jobId, token) {
  const res = await fetch(`${BASE}/api/jobs/${jobId}/proof`, { headers: authHeaders(token) });
  return res.ok ? res.json() : null;
}

// ── Files ─────────────────────────────────────────────────────────────────────

export async function getWorkspaceFiles(jobId, token) {
  // Try adapter endpoint
  try {
    const res = await fetch(`${BASE}/api/builds/${jobId}/files`, { headers: authHeaders(token) });
    if (res.ok) return res.json(); // returns tree format
  } catch {}
  // Fall back to our workspace endpoint
  const res = await fetch(`${BASE}/api/jobs/${jobId}/workspace/files`, { headers: authHeaders(token) });
  return res.ok ? (await res.json()).files || [] : [];
}

export async function getFileContent(jobId, path, token) {
  try {
    const res = await fetch(`${BASE}/api/builds/${jobId}/file?path=${encodeURIComponent(path)}`, { headers: authHeaders(token) });
    if (res.ok) return res.text();
  } catch {}
  const res = await fetch(`${BASE}/api/jobs/${jobId}/workspace/file?path=${encodeURIComponent(path)}`, { headers: authHeaders(token) });
  return res.ok ? (await res.json()).content || '' : '';
}

export function getDownloadURL(jobId, jobStatus) {
  return `${BASE}/api/jobs/${encodeURIComponent(jobId)}/workspace/download${workspaceZipQuery(jobStatus)}`;
}

// ── Preview ───────────────────────────────────────────────────────────────────

export async function getPreviewStatus(jobId, token) {
  try {
    const res = await fetch(`${BASE}/api/builds/${jobId}/preview`, { headers: authHeaders(token) });
    if (res.ok) return res.json();
  } catch {}
  // Derive from job
  const job = await getJobStatus(jobId, token);
  const url = job?.dev_server_url || job?.preview_url || job?.published_url || job?.deploy_url;
  return { url, available: !!url, phase: job?.status === 'completed' ? 'live' : 'building' };
}

// ── Deploy ────────────────────────────────────────────────────────────────────

export async function deployBuild(jobId, target = 'railway', token) {
  const res = await fetch(`${BASE}/api/builds/${jobId}/deploy`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify({ target }),
  });
  return res.ok ? res.json() : { status: 'failed', url: '' };
}

// ── Workflows ─────────────────────────────────────────────────────────────────

export async function getWorkflows(token) {
  const res = await fetch(`${BASE}/api/workflows`, { headers: authHeaders(token) });
  return res.ok ? res.json() : { workflows: {}, total: 0 };
}

export async function runWorkflow(workflowKey, projectId, token) {
  const res = await fetch(`${BASE}/api/workflows/run`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify({ workflow_key: workflowKey, project_id: projectId }),
  });
  return res.ok ? res.json() : { success: false };
}

// ── Spawn ─────────────────────────────────────────────────────────────────────

export async function runSpawn({ jobId, task, config, context, token }) {
  const res = await fetch(`${BASE}/api/spawn/run`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify({ jobId, task, config, context }),
  });
  return res.ok ? res.json() : { consensus: null, confidence: 0, subagentResults: [] };
}

// ── Automation ────────────────────────────────────────────────────────────────

export async function createAutomation({ jobId, description, token }) {
  const res = await fetch(`${BASE}/api/builds/${jobId}/automation`, {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify({ description }),
  });
  return res.ok ? res.json() : { status: 'failed' };
}

// ── WebSocket connection ───────────────────────────────────────────────────────

export function createWebSocket(jobId) {
  const wsBase = BASE.replace('https://', 'wss://').replace('http://', 'ws://');
  try {
    return new WebSocket(`${wsBase}/ws/events?jobId=${jobId}`);
  } catch {
    return null;
  }
}

// ── Trust / Quality ───────────────────────────────────────────────────────────

export async function getTrustScore(jobId, token) {
  const res = await fetch(`${BASE}/api/builds/${jobId}/trust`, { headers: authHeaders(token) });
  return res.ok ? res.json() : { qualityScore: 0, passed: false };
}
