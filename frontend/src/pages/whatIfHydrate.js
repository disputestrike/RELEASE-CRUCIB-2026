/**
 * Maps GET /api/simulations/:id/runs/:runId detail payload into the same shape used by POST /simulations/run.
 */

function simulationPulseFromDetails(details) {
  const run = details.run || {};
  if (Array.isArray(run.simulation_pulse) && run.simulation_pulse.length) {
    return run.simulation_pulse;
  }
  const replay = Array.isArray(details.replay_events) ? details.replay_events : [];
  const fromReplay = replay
    .filter((e) => (e.event_type || '') === 'simulation.pulse')
    .map((e) => e.event_payload || {});
  return fromReplay.length ? fromReplay : [];
}

function firstTrust(details) {
  const run = details.run || {};
  if (run.trust_score && typeof run.trust_score === 'object') return run.trust_score;
  const rows = Array.isArray(details.trust_scores) ? details.trust_scores : [];
  const row = rows[0];
  if (!row || typeof row !== 'object') {
    return { trust_score: 0.5, components: {}, warnings: [], score: 0.5 };
  }
  return {
    trust_score: row.trust_score ?? row.score ?? 0.5,
    score: row.score ?? row.trust_score,
    components: row.components || {},
    warnings: Array.isArray(row.warnings) ? row.warnings : [],
    formula: row.formula,
    evidence_policy: row.evidence_policy,
  };
}

/** @param {Record<string, unknown>} details Response from GET /api/simulations/{simulation_id}/runs/{run_id} */
export function hydrateSimulationDetail(details) {
  const run = details.run || {};
  const inputs = Array.isArray(details.inputs) ? details.inputs : [];
  const classification =
    run.classification ||
    (inputs[0] && inputs[0].classification) ||
    {};
  const pmRow = Array.isArray(details.population_models) ? details.population_models[0] : null;
  let population_model = {};
  if (pmRow && typeof pmRow === 'object') {
    population_model = {
      population_size: pmRow.population_size,
      summary: pmRow.summary,
      method: pmRow.method,
      clusters: Array.isArray(pmRow.clusters) ? pmRow.clusters : [],
      warnings: Array.isArray(pmRow.warnings) ? pmRow.warnings : [],
      schema_version: pmRow.schema_version,
    };
  }
  const report = run.report || {};
  if (
    population_model &&
    (!population_model.clusters || population_model.clusters.length === 0) &&
    report.population_model
  ) {
    const rp = report.population_model;
    population_model = {
      ...population_model,
      population_size: rp.population_size ?? population_model.population_size,
      summary: rp.summary ?? population_model.summary,
      clusters: Array.isArray(rp.clusters) ? rp.clusters : population_model.clusters,
      warnings: rp.warnings ?? population_model.warnings,
    };
  }

  return {
    engine: run.engine || 'Reality Engine',
    classification,
    sources: Array.isArray(details.sources) ? details.sources : [],
    evidence: Array.isArray(details.evidence) ? details.evidence : [],
    claims: Array.isArray(details.claims) ? details.claims : [],
    missing_evidence: run.missing_evidence || [],
    unsupported_claims: run.unsupported_claims || [],
    assumptions: Array.isArray(details.assumptions) ? details.assumptions : [],
    agents: Array.isArray(details.agents) ? details.agents : [],
    rounds: Array.isArray(details.rounds) ? details.rounds : [],
    agent_messages: Array.isArray(details.agent_messages) ? details.agent_messages : [],
    belief_updates: Array.isArray(details.belief_updates) ? details.belief_updates : [],
    clusters: Array.isArray(details.clusters) ? details.clusters : [],
    outcomes: Array.isArray(details.outcomes) ? details.outcomes : [],
    recommendation: run.recommendation || report.recommendation || null,
    final_verdict: run.final_verdict || report.final_verdict || {},
    trust_score: firstTrust(details),
    report,
    population_model,
    simulation: details.simulation || null,
    run,
    replay_events: Array.isArray(details.replay_events) ? details.replay_events : [],
    events: Array.isArray(details.events) ? details.events : [],
    simulation_pulse: simulationPulseFromDetails(details),
    debate_engine_mode: details.debate_engine_mode ?? run.debate_engine_mode ?? null,
    debate_augment: details.debate_augment ?? run.debate_augment ?? null,
    output_answer: run.output_answer || report.output_answer || {},
    routed_intent: run.routed_intent || report.routed_intent || null,
    retrieval_ledger: run.retrieval_ledger ?? null,
  };
}
