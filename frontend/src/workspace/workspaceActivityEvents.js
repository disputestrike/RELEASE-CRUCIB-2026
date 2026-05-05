export function humanizeActivityAgentLabel(raw) {
  const t = String(raw || '').trim();
  if (!t) return 'Step';
  const noAgents = t.replace(/^agents\./i, '');
  const spaced = noAgents.replace(/[._]+/g, ' ').replace(/\s+/g, ' ').trim();
  if (!spaced) return 'Step';
  return spaced.replace(/\b\w/g, (c) => c.toUpperCase());
}

function payloadFromEvent(ev) {
  const direct = ev?.payload && typeof ev.payload === 'object' ? ev.payload : {};
  if (Object.keys(direct).length) return direct;
  if (typeof ev?.payload === 'string' && ev.payload.trim()) {
    try {
      const parsed = JSON.parse(ev.payload);
      return parsed && typeof parsed === 'object' ? parsed : {};
    } catch {
      return {};
    }
  }
  try {
    return JSON.parse(ev?.payload_json || '{}');
  } catch {
    return {};
  }
}

function shortPath(path) {
  const s = String(path || '').trim();
  if (!s) return '';
  return s.split('/').pop() || s;
}

export function formatWorkspaceActivityEvent(ev) {
  const t = ev?.type || ev?.event_type;
  const payload = payloadFromEvent(ev);
  const name = humanizeActivityAgentLabel(
    payload.agent_name || payload.step_key || payload.step || ev?.step || payload.node_key || '',
  );
  switch (t) {
    case 'step_created':
      return name && name !== 'Step' ? `Queued: ${name}` : 'Step queued';
    case 'step_started':
      return name && name !== 'Step' ? `Working on: ${name}` : 'Working on the next step';
    case 'step_status_changed': {
      const status = String(payload.status || '').replace(/_/g, ' ');
      return status ? `Step status: ${status}` : null;
    }
    case 'step_completed':
      return name && name !== 'Step' ? `Done: ${name}` : 'Step completed';
    case 'step_failed':
      return name && name !== 'Step' ? `Fixing: ${name}` : 'Fixing the next item';
    case 'step_retrying':
      return name && name !== 'Step' ? `Retrying: ${name}` : 'Retrying step';
    case 'job_started':
      return 'Runtime started';
    case 'runtime_backend_selected':
      return 'Build runtime selected';
    case 'pipeline_dispatch':
    case 'pipeline_started':
      return 'Build runtime started';
    case 'runtime_steps_cleared':
      return 'Runtime rows refreshed';
    case 'runtime_resume_prepared':
      return 'Runtime resumed';
    case 'plan_created':
      return 'Work checklist ready';
    case 'tool_call': {
      const tool = payload.tool || payload.name || payload.tool_name || 'Tool';
      const target = payload.input || payload.command || payload.path || payload.pattern || '';
      return target ? `${tool}: ${String(target).slice(0, 120)}` : `${tool}: running`;
    }
    case 'tool_result': {
      const tool = payload.tool || payload.name || payload.tool_name || 'Tool';
      if (payload.success === false) return `${tool}: needs fix`;
      return `${tool}: done`;
    }
    case 'verifier_started':
      return 'Proof: running build checks';
    case 'verifier_passed':
      return 'Proof: build checks passed';
    case 'verifier_failed':
      return 'Proof: build check needs repair';
    case 'repair_started':
      return 'Repairing from proof error';
    case 'repair_completed':
      return payload.passed === false ? 'Proof still needs work' : 'Proof rerun complete';
    case 'job_completed':
      return 'Workspace ready';
    case 'job_status_changed': {
      const status = String(payload.status || '').replace(/_/g, ' ');
      return status ? `Job status: ${status}` : null;
    }
    case 'job_failed': {
      return 'Proof failed - details available';
    }
    case 'dag_node_started':
      return name && name !== 'Step' ? `Starting ${name}` : 'Starting next task';
    case 'dag_node_completed': {
      const files = payload.output_files;
      if (Array.isArray(files) && files.length) {
        const short = files.slice(0, 4).map(shortPath);
        return `Wrote ${files.length} file(s): ${short.join(', ')}${files.length > 4 ? '...' : ''}`;
      }
      return name && name !== 'Step' ? `Done: ${name}` : 'Task completed';
    }
    case 'artifact_delta': {
      const changed = Number(payload.changed || payload.changed_count || 0);
      const added = Number(payload.added || payload.added_count || 0);
      const removed = Number(payload.removed || payload.removed_count || 0);
      const total = changed + added + removed;
      return total > 0 ? `Files changed: ${added} added, ${changed} updated, ${removed} removed` : 'Files checked: no delta';
    }
    case 'file_written': {
      const path = String(payload.path || '').trim();
      const base = shortPath(path);
      return base ? `Saved file: ${base}` : 'File written';
    }
    case 'code_repair_applied': {
      const files = Array.isArray(payload.files) ? payload.files : [];
      const label = payload.failure_type ? ` after ${String(payload.failure_type).replace(/_/g, ' ')}` : '';
      return files.length
        ? `Repair applied${label}: ${files.slice(0, 3).map(shortPath).join(', ')}${files.length > 3 ? '...' : ''}`
        : `Repair applied${label}`;
    }
    case 'user_steering':
      return 'Steering applied';
    case 'job_reactivated':
      return 'Run reactivated';
    case 'brain_guidance':
      if (payload.headline) return String(payload.headline).trim().slice(0, 160);
      if (payload.summary) return String(payload.summary).trim().slice(0, 160);
      return 'Brain update';
    case 'workspace_transcript': {
      const isAsst = payload.role === 'assistant';
      const line = String(payload.text || payload.body || '').trim().slice(0, 120);
      if (!line) return null;
      return isAsst ? `Reply: ${line}` : `You: ${line}`;
    }
    case 'preflight_report': {
      const pf = payload.preflight || payload;
      const n = Array.isArray(pf?.issues) ? pf.issues.length : 0;
      if (pf?.passed === true && n === 0) return 'Preflight: environment OK';
      if (pf?.passed === true) return `Preflight: OK (${n} note(s))`;
      if (pf?.passed === false) return `Preflight: ${n || 'some'} issue(s) (run may still proceed)`;
      return n ? `Preflight: ${n} note(s)` : 'Preflight: completed';
    }
    case 'spec_guardian': {
      const sg = payload.spec_guard || payload;
      if (sg?.blocks_run) return 'Spec check: blocked run (goal out of template scope)';
      return 'Spec check: OK';
    }
    case 'brain_prebuild_briefing': {
      const sim = payload.similar_builds_found;
      const pred = Array.isArray(payload.predicted_failures) ? payload.predicted_failures.length : 0;
      if (typeof sim === 'number' && sim > 0) return `Pre-build: ${sim} similar past build(s); ${pred} risk flag(s)`;
      if (pred > 0) return `Pre-build: ${pred} predicted risk(s)`;
      return payload.intelligence_available ? 'Pre-build intelligence loaded' : null;
    }
    case 'verification_result': {
      const ok = payload.passed === true || payload.passed === 'true';
      const sc = payload.score;
      if (ok) return typeof sc === 'number' ? `Proof: passed (${sc})` : 'Proof: passed';
      return typeof sc === 'number' ? `Proof: needs work (${sc})` : 'Proof: needs work';
    }
    case 'verification_attempt_failed':
      return 'Checking again after an update';
    case 'step_retry_exhausted':
      return 'Continuing with a smaller fix pass';
    case 'step_infrastructure_failure':
      return 'Infrastructure issue: run stopped for a host or dependency failure';
    case 'step_verifying':
      return name && name !== 'Step' ? `Checking proof: ${name}` : 'Checking proof';
    case 'scheduler_deadlock_detected':
      return 'Scheduler: deadlock resolved';
    case 'execution_authority':
      return payload?.mode ? `Execution authority: ${payload.mode}` : null;
    default:
      return null;
  }
}
