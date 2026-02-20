import React, { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Bot, CheckCircle, Clock, AlertCircle, Zap,
  ChevronDown, ChevronRight, Loader2, RefreshCw, ShieldCheck
} from 'lucide-react';
import './InlineAgentMonitor.css';

/**
 * InlineAgentMonitor — Shows agent activity inline in the center panel during BUILD state
 * 
 * This is the differentiator: no competitor shows 120+ agents working live.
 * Displays:
 *   - Overall progress bar with phase name
 *   - Agent grid organized by layer (Planning, Execution, Validation, Deployment)
 *   - Per-agent status icon, progress bar, token count
 *   - Live event timeline
 *   - Total token usage
 */

const AGENT_LAYERS = {
  planning: {
    label: 'Planning',
    color: '#1A1A1A',
    agents: ['Planner', 'Requirements Clarifier', 'Stack Selector']
  },
  execution: {
    label: 'Execution',
    color: '#808080',
    agents: ['Frontend Generation', 'Backend Generation', 'Database Agent', 'API Integration', 'Test Generation']
  },
  validation: {
    label: 'Validation',
    color: '#FF8F5E',
    agents: ['Security Checker', 'Test Executor', 'UX Auditor', 'Performance Analyzer']
  },
  deployment: {
    label: 'Deployment',
    color: '#F59E0B',
    agents: ['Deployment Agent', 'Error Recovery', 'Memory Agent']
  }
};

const InlineAgentMonitor = ({
  isBuilding = false,
  buildProgress = 0,
  currentPhase = '',
  agentsActivity = [],
  buildEvents = [],
  tokensUsed = 0,
  projectBuildProgress = {},
  qualityScore = null,
  onRetry,
}) => {
  const [expandedLayers, setExpandedLayers] = useState({ planning: true, execution: true, validation: false, deployment: false });
  const [showTimeline, setShowTimeline] = useState(false);

  // Auto-expand layers as build progresses
  useEffect(() => {
    if (!isBuilding) return;
    const phase = (currentPhase || '').toLowerCase();
    if (phase.includes('plan')) {
      setExpandedLayers(prev => ({ ...prev, planning: true }));
    } else if (phase.includes('generat') || phase.includes('build') || phase.includes('execut')) {
      setExpandedLayers(prev => ({ ...prev, execution: true }));
    } else if (phase.includes('valid') || phase.includes('test') || phase.includes('check')) {
      setExpandedLayers(prev => ({ ...prev, validation: true }));
    } else if (phase.includes('deploy')) {
      setExpandedLayers(prev => ({ ...prev, deployment: true }));
    }
  }, [currentPhase, isBuilding]);

  // Derive agent statuses from activity data
  const agentStatuses = useMemo(() => {
    const statusMap = {};
    agentsActivity.forEach(a => {
      const name = a.agent_name || a.agent || a.message?.split(' ')[0] || '';
      if (name) {
        statusMap[name] = {
          status: a.status || (a.completed ? 'completed' : 'running'),
          progress: a.progress || 0,
          tokens_used: a.tokens_used || 0,
          message: a.message || '',
        };
      }
    });
    return statusMap;
  }, [agentsActivity]);

  const getAgentStatus = (agentName) => {
    return agentStatuses[agentName] || { status: 'idle', progress: 0, tokens_used: 0 };
  };

  const completedCount = Object.values(agentStatuses).filter(a => a.status === 'completed').length;
  const runningCount = Object.values(agentStatuses).filter(a => a.status === 'running').length;
  const totalAgents = Object.values(AGENT_LAYERS).reduce((sum, l) => sum + l.agents.length, 0);

  const toggleLayer = (layer) => {
    setExpandedLayers(prev => ({ ...prev, [layer]: !prev[layer] }));
  };

  if (!isBuilding && buildProgress === 0) return null;

  return (
    <div className="inline-agent-monitor">
      {/* Header */}
      <div className="iam-header">
        <div className="iam-header-left">
          <div className="iam-pulse-dot" />
          <span className="iam-header-title">
            {isBuilding ? 'Building...' : buildProgress >= 100 ? 'Build Complete' : 'Build Progress'}
          </span>
          <span className="iam-header-stats">
            {completedCount}/{totalAgents} agents
            {runningCount > 0 && <span className="iam-running-badge">{runningCount} active</span>}
          </span>
        </div>
        <div className="iam-header-right">
          <div className="iam-token-badge">
            <Zap size={14} />
            <span>{(tokensUsed || projectBuildProgress?.tokens_used || 0).toLocaleString()}</span>
          </div>
        </div>
      </div>

      {/* Progress bar */}
      <div className="iam-progress-container">
        {currentPhase && (
          <div className="iam-phase-label">{currentPhase}</div>
        )}
        <div className="iam-progress-track">
          <motion.div
            className="iam-progress-fill"
            initial={{ width: 0 }}
            animate={{ width: `${buildProgress}%` }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
          />
        </div>
        <div className="iam-progress-text">{Math.round(buildProgress)}%</div>
      </div>

      {/* Agent Grid by Layer */}
      <div className="iam-layers">
        {Object.entries(AGENT_LAYERS).map(([layerKey, layer]) => (
          <div key={layerKey} className="iam-layer">
            <button
              className="iam-layer-header"
              onClick={() => toggleLayer(layerKey)}
            >
              <div className="iam-layer-dot" style={{ background: layer.color }} />
              <span className="iam-layer-label">{layer.label}</span>
              <span className="iam-layer-count">
                {layer.agents.filter(a => getAgentStatus(a).status === 'completed').length}/{layer.agents.length}
              </span>
              {expandedLayers[layerKey] ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            </button>

            <AnimatePresence>
              {expandedLayers[layerKey] && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="iam-layer-agents"
                >
                  {layer.agents.map(agentName => {
                    const agent = getAgentStatus(agentName);
                    return (
                      <div
                        key={agentName}
                        className={`iam-agent ${agent.status}`}
                      >
                        <div className="iam-agent-icon">
                          {agent.status === 'completed' && <CheckCircle size={14} style={{ color: '#808080' }} />}
                          {agent.status === 'running' && <Loader2 size={14} className="iam-spin" style={{ color: layer.color }} />}
                          {agent.status === 'failed' && <AlertCircle size={14} style={{ color: '#EF4444' }} />}
                          {agent.status === 'idle' && <Clock size={14} style={{ color: '#9CA3AF' }} />}
                        </div>
                        <span className="iam-agent-name">{agentName}</span>
                        {agent.status === 'running' && (
                          <div className="iam-agent-progress">
                            <div className="iam-agent-progress-fill" style={{ width: `${agent.progress}%`, background: layer.color }} />
                          </div>
                        )}
                        <span className="iam-agent-tokens">
                          {agent.tokens_used > 0 ? `${(agent.tokens_used / 1000).toFixed(1)}k` : '—'}
                        </span>
                      </div>
                    );
                  })}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        ))}
      </div>

      {/* Event Timeline Toggle */}
      {buildEvents.length > 0 && (
        <div className="iam-timeline-section">
          <button
            className="iam-timeline-toggle"
            onClick={() => setShowTimeline(!showTimeline)}
          >
            {showTimeline ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            <span>Event Timeline ({buildEvents.length})</span>
          </button>
          {showTimeline && (
            <div className="iam-timeline">
              {buildEvents.slice(-20).map((ev, i) => (
                <div key={ev.id ?? i} className="iam-timeline-event">
                  <span className="iam-timeline-time">
                    {ev.ts ? new Date(ev.ts).toLocaleTimeString() : ''}
                  </span>
                  <span className={`iam-timeline-type ${ev.type?.includes('completed') ? 'completed' : ev.type?.includes('started') ? 'started' : 'other'}`}>
                    {ev.type === 'agent_started' && `${ev.agent || 'agent'} started`}
                    {ev.type === 'agent_completed' && `${ev.agent || 'agent'} completed`}
                    {ev.type === 'phase_started' && (ev.message || 'phase')}
                    {ev.type === 'build_started' && 'Build started'}
                    {ev.type === 'build_completed' && `Build ${ev.status || 'done'}`}
                    {!['agent_started','agent_completed','phase_started','build_started','build_completed'].includes(ev.type) && (ev.message || ev.type)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Quality Score — shown after build completes (Test A-13) */}
      {!isBuilding && buildProgress >= 100 && qualityScore != null && (
        <div className="iam-quality-score">
          <ShieldCheck size={16} style={{ color: qualityScore >= 80 ? '#808080' : qualityScore >= 50 ? '#F59E0B' : '#EF4444' }} />
          <span className="iam-quality-label">Quality Score</span>
          <span className="iam-quality-value" style={{ color: qualityScore >= 80 ? '#808080' : qualityScore >= 50 ? '#F59E0B' : '#EF4444' }}>
            {qualityScore}/100
          </span>
        </div>
      )}

      {/* Retry button when build failed */}
      {!isBuilding && buildProgress > 0 && buildProgress < 100 && onRetry && (
        <button className="iam-retry-btn" onClick={onRetry}>
          <RefreshCw size={14} />
          <span>Retry Build</span>
        </button>
      )}
    </div>
  );
};

export default InlineAgentMonitor;
