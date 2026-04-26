import React, { useMemo, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  Brain,
  CheckCircle2,
  FileText,
  GitBranch,
  Loader2,
  Play,
  RadioTower,
  Search,
  ShieldCheck,
  Users,
} from 'lucide-react';
import { useAuth } from '../authContext';
import { API_BASE as API } from '../apiBase';
import VoiceInput from '../components/VoiceInput';
import './WhatIfPage.css';

const PROMPTS = [
  'Will the Lakers win the NBA championship?',
  'Should we raise prices by 30% next quarter?',
  'What happens if Nigeria bans crypto?',
  'Should we migrate off AWS?',
  'Will customers hate this redesign?',
];

function pct(value) {
  const n = Number(value || 0);
  return `${Math.round(n * 100)}%`;
}

async function readJsonResponse(response, label) {
  const contentType = response.headers.get('content-type') || '';
  const body = await response.text();
  const preview = body.slice(0, 180).replace(/\s+/g, ' ').trim();

  if (!response.ok) {
    throw new Error(`${label} failed (${response.status}). ${preview}`);
  }
  if (!contentType.toLowerCase().includes('application/json')) {
    throw new Error(`${label} returned ${contentType || 'non-JSON'} instead of JSON. ${preview}`);
  }
  try {
    return JSON.parse(body);
  } catch (err) {
    throw new Error(`${label} returned invalid JSON. ${preview}`);
  }
}

function Panel({ title, icon, children, aside }) {
  const Icon = icon || Activity;
  return (
    <section className="sim-panel">
      <div className="sim-panel-head">
        <div className="sim-panel-title"><Icon size={15} /> {title}</div>
        {aside && <div className="sim-panel-aside">{aside}</div>}
      </div>
      {children}
    </section>
  );
}

export default function WhatIfPage() {
  const { token } = useAuth();
  const [prompt, setPrompt] = useState(PROMPTS[0]);
  const [assumptionsText, setAssumptionsText] = useState('');
  const [depth, setDepth] = useState('balanced');
  const [attachments, setAttachments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);

  const assumptions = useMemo(
    () => assumptionsText.split('\n').map((row) => row.trim()).filter(Boolean),
    [assumptionsText],
  );

  const runSimulation = async () => {
    const cleanPrompt = String(prompt || '').trim();
    if (!cleanPrompt) {
      setError('Enter a scenario to simulate.');
      return;
    }
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const headers = {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      };
      const createRes = await fetch(`${API}/simulations`, {
        method: 'POST',
        credentials: 'include',
        headers,
        body: JSON.stringify({
          prompt: cleanPrompt,
          assumptions,
          attachments,
          metadata: { surface: 'simulation_command_center' },
        }),
      });
      const created = await readJsonResponse(createRes, 'Create simulation');
      const simulationId = created?.simulation?.id;
      if (!simulationId) throw new Error('Simulation create response did not include an id.');

      const runPayload = {
        simulation_id: simulationId,
        prompt: cleanPrompt,
        assumptions,
        attachments,
        depth,
        use_live_evidence: true,
        metadata: { surface: 'simulation_command_center', depth },
      };
      const runRes = await fetch(`${API}/simulations/run`, {
        method: 'POST',
        credentials: 'include',
        headers,
        body: JSON.stringify(runPayload),
      });
      try {
        setResult(await readJsonResponse(runRes, 'Run simulation'));
      } catch (runErr) {
        const fallbackRes = await fetch(`${API}/runtime/what-if`, {
          method: 'POST',
          credentials: 'include',
          headers,
          body: JSON.stringify({
            scenario: cleanPrompt,
            assumptions,
            attachments,
            depth,
            metadata: { surface: 'simulation_command_center', fallback_from: 'simulations_run', depth },
          }),
        });
        const fallback = await readJsonResponse(fallbackRes, 'Run simulation fallback');
        setResult({ ...fallback, fallback_used: 'runtime_what_if' });
      }
    } catch (err) {
      setError(err?.message || 'Simulation failed.');
    } finally {
      setLoading(false);
    }
  };

  const classification = result?.classification || {};
  const trust = result?.trust_score || {};
  const report = result?.report || {};
  const agents = Array.isArray(result?.agents) ? result.agents : [];
  const messages = Array.isArray(result?.agent_messages) ? result.agent_messages : [];
  const updates = Array.isArray(result?.belief_updates) ? result.belief_updates : [];
  const outcomes = Array.isArray(result?.outcomes) ? result.outcomes : [];
  const evidence = Array.isArray(result?.evidence) ? result.evidence : [];
  const sources = Array.isArray(result?.sources) ? result.sources : [];
  const populationModel = result?.population_model || report?.population_model || {};
  const populationClusters = Array.isArray(populationModel?.clusters) ? populationModel.clusters : [];
  const missingEvidence = Array.isArray(result?.missing_evidence) ? result.missing_evidence : [];
  const unsupportedClaims = Array.isArray(result?.unsupported_claims) ? result.unsupported_claims : [];

  return (
    <div className="simulation-page">
      <header className="simulation-hero">
        <div className="simulation-kicker"><RadioTower size={14} /> Reality Engine</div>
        <h1>Simulation</h1>
        <p>
          Ask any scenario. CrucibAI classifies it, identifies evidence needs, creates
          scenario-specific agents, runs debate rounds, tracks belief shifts, and produces
          an auditable report with trust scoring.
        </p>
      </header>

      <Panel title="Universal Input" icon={Search}>
        <textarea
          className="simulation-prompt"
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          rows={5}
          placeholder="Ask any forecast, decision, market reaction, product, sports, business, finance, policy, or engineering scenario..."
        />
        <div className="simulation-input-tools">
          <VoiceInput
            apiEndpoint={API}
            token={token}
            disabled={loading}
            onTranscribed={(text) => {
              setPrompt((current) => {
                const existing = String(current || '').trim();
                return existing ? `${existing}\n${text}` : text;
              });
            }}
          />
        </div>
        <div className="simulation-presets">
          {PROMPTS.map((item) => (
            <button type="button" key={item} onClick={() => setPrompt(item)}>
              {item}
            </button>
          ))}
        </div>
        <textarea
          className="simulation-assumptions"
          value={assumptionsText}
          onChange={(event) => setAssumptionsText(event.target.value)}
          rows={3}
          placeholder="Optional assumptions, one per line. Example: LeBron is healthy. CAC is $90. Railway is the target host."
        />
        <div className="simulation-controls">
          <fieldset className="simulation-depth">
            <legend>Simulation Depth</legend>
            {[
              ['fast', 'Fast', 'Quick read with light evidence retrieval.'],
              ['balanced', 'Balanced', 'Best default for most decisions and forecasts.'],
              ['deep', 'Deep', 'More evidence, debate, and population modeling.'],
              ['maximum', 'Maximum', 'Largest audited run for high-stakes scenarios.'],
            ].map(([value, label, description]) => (
              <button
                type="button"
                key={value}
                className={depth === value ? 'active' : ''}
                onClick={() => setDepth(value)}
              >
                <strong>{label}</strong>
                <span>{description}</span>
              </button>
            ))}
          </fieldset>
          <label className="simulation-file">
            <span>Attachments</span>
            <input
              type="file"
              multiple
              onChange={(event) => {
                const files = Array.from(event.target.files || []);
                setAttachments(files.map((file) => ({ name: file.name, size: file.size, type: file.type || 'unknown' })));
              }}
            />
          </label>
        </div>
        {attachments.length > 0 && (
          <div className="simulation-attachments">
            {attachments.map((file) => <span key={`${file.name}-${file.size}`}>{file.name}</span>)}
          </div>
        )}
        <div className="simulation-actions">
          <button type="button" className="simulation-run" onClick={runSimulation} disabled={loading}>
            {loading ? <Loader2 size={15} className="spin" /> : <Play size={15} />}
            {loading ? 'Running Simulation...' : 'Run Simulation'}
          </button>
          {error && <span className="simulation-error"><AlertTriangle size={14} /> {error}</span>}
        </div>
      </Panel>

      {result && (
        <>
          <Panel title="Auto-Detected Scenario" icon={Brain} aside={result.engine}>
            <div className="simulation-grid four">
              <div><span>Domain</span><strong>{classification.domain}</strong></div>
              <div><span>Scenario type</span><strong>{String(classification.scenario_type || '').replaceAll('_', ' ')}</strong></div>
              <div><span>Time sensitivity</span><strong>{classification.time_sensitivity}</strong></div>
              <div><span>Output style</span><strong>{String(classification.output_style || '').replaceAll('_', ' ')}</strong></div>
            </div>
            <p className="simulation-interpretation">{classification.interpretation}</p>
            {Array.isArray(classification.required_evidence) && (
              <div className="simulation-chips">
                {classification.required_evidence.map((item) => <span key={item}>{item}</span>)}
              </div>
            )}
          </Panel>

          <Panel title="Evidence Panel" icon={FileText} aside={`${sources.length} sources / ${evidence.length} facts`}>
            <div className="simulation-evidence-layout">
              <div>
                <h3>Sources used</h3>
                {sources.map((source) => (
                  <div className="simulation-source" key={source.id}>
                    <strong>{source.title}</strong>
                    <span>{source.type} / reliability: {source.reliability} / freshness: {source.freshness}</span>
                  </div>
                ))}
              </div>
              <div>
                <h3>Evidence gaps</h3>
                {missingEvidence.map((item) => <div className="simulation-gap" key={item}>{item}</div>)}
                {unsupportedClaims.map((item) => <div className="simulation-warning" key={item}>{item}</div>)}
              </div>
            </div>
          </Panel>

          <Panel title="Agent Arena" icon={Users} aside={`${agents.length} core agents`}>
            <div className="simulation-agent-grid">
              {agents.map((agent) => (
                <div className="simulation-agent" key={agent.id}>
                  <div className="simulation-agent-head">
                    <strong>{agent.role}</strong>
                    <span>{pct(agent.current_belief)}</span>
                  </div>
                  <p>{agent.domain_expertise}</p>
                  <div className="simulation-meter"><i style={{ width: pct(agent.current_belief) }} /></div>
                  {agent.latest_argument && <p>{agent.latest_argument}</p>}
                  <footer>confidence {pct(agent.confidence)} / {agent.persona}</footer>
                </div>
              ))}
            </div>
          </Panel>

          <Panel title="Population Reaction" icon={RadioTower} aside={populationModel.population_size ? `${Number(populationModel.population_size).toLocaleString()} perspectives` : 'modeled perspectives'}>
            <p className="simulation-interpretation">{populationModel.summary || 'Population modeling will appear when a run completes.'}</p>
            <div className="simulation-population-grid">
              {populationClusters.map((cluster) => (
                <div className="simulation-population" key={cluster.id || cluster.label}>
                  <div className="simulation-outcome-head">
                    <strong>{cluster.label}</strong>
                    <span>{pct(cluster.share)}</span>
                  </div>
                  <div className="simulation-meter"><i style={{ width: pct(cluster.share) }} /></div>
                  <p>{cluster.rationale}</p>
                  <footer>{Number(cluster.size || 0).toLocaleString()} modeled perspectives / {cluster.expected_shift}</footer>
                </div>
              ))}
            </div>
            {(populationModel.warnings || []).map((warning) => (
              <div className="simulation-warning" key={warning}><AlertTriangle size={13} /> {warning}</div>
            ))}
          </Panel>

          <Panel title="Debate Timeline" icon={GitBranch}>
            <div className="simulation-timeline">
              {(result.rounds || []).map((round) => {
                const roundMessages = messages.filter((msg) => msg.round_id === round.id).slice(0, 3);
                const roundUpdates = updates.filter((update) => update.round_id === round.id).slice(0, 3);
                return (
                  <div className="simulation-round" key={round.id}>
                    <div className="simulation-round-head">
                      <strong>Round {round.round_number}</strong>
                      <span>{round.purpose}</span>
                    </div>
                    {roundMessages.map((msg) => <p key={msg.id}>{msg.content}</p>)}
                    {roundUpdates.map((update) => (
                      <div className="simulation-belief" key={update.id}>
                        belief {pct(update.previous_belief)} -> {pct(update.new_belief)} / {update.reason}
                      </div>
                    ))}
                  </div>
                );
              })}
            </div>
          </Panel>

          <Panel title="Outcomes" icon={Activity}>
            <div className="simulation-outcomes">
              {outcomes.map((outcome) => (
                <div className="simulation-outcome" key={outcome.id}>
                  <div className="simulation-outcome-head">
                    <strong>{outcome.label}</strong>
                    <span>{outcome.display_likelihood}</span>
                  </div>
                  <p>{outcome.rationale}</p>
                  <h4>What would change it</h4>
                  {(outcome.what_would_change || []).slice(0, 3).map((item) => <em key={item}>{item}</em>)}
                </div>
              ))}
            </div>
          </Panel>

          <Panel title="Trust Panel" icon={ShieldCheck} aside={trust.trust_score}>
            <div className="simulation-trust-grid">
              {Object.entries(trust.components || {}).map(([key, value]) => (
                <div key={key}>
                  <span>{key.replaceAll('_', ' ')}</span>
                  <strong>{pct(value)}</strong>
                </div>
              ))}
            </div>
            {(trust.warnings || []).map((warning) => (
              <div className="simulation-warning" key={warning}><AlertTriangle size={13} /> {warning}</div>
            ))}
          </Panel>

          <Panel title="Final Report" icon={CheckCircle2}>
            <div className="simulation-report">
              <h3>{report.executive_summary}</h3>
              <p>{result.recommendation?.recommendation}</p>
              <h4>Next data to collect</h4>
              <ul>
                {(report.next_data_to_collect || []).map((item) => <li key={item}>{item}</li>)}
              </ul>
              <div className="simulation-replay">
                Simulation {report.replay_metadata?.simulation_id} / Run {report.replay_metadata?.run_id}
              </div>
            </div>
          </Panel>
        </>
      )}
    </div>
  );
}
