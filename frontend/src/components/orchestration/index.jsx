// frontend/src/components/orchestration/PhaseGroup.jsx
import React from 'react';
import AgentCard from './AgentCard';
import ProgressBar from './ProgressBar';
import styles from './orchestration.module.css';

export default function PhaseGroup({ phase, phaseIndex, totalPhases, isExpanded, onToggle }) {
  const statusColors = {
    'complete': '#28A745',
    'running': '#FFC107',
    'queued': '#6C757D',
    'error': '#DC3545'
  };

  const statusIcon = {
    'complete': '✓',
    'running': '▶',
    'queued': '⧖',
    'error': '✕'
  };

  return (
    <div 
      className={`${styles.phaseGroup} ${isExpanded ? styles.expanded : ''}`}
      style={{ borderLeftColor: statusColors[phase.status] }}
    >
      {/* Phase Header */}
      <div className={styles.phaseHeader} onClick={onToggle}>
        <div className={styles.phaseTitle}>
          <span className={styles.statusIcon} style={{ color: statusColors[phase.status] }}>
            {statusIcon[phase.status]}
          </span>
          <h3>{phase.name}</h3>
          <span className={styles.phaseStats}>
            ({phase.completed}/{phase.total})
          </span>
        </div>

        <div className={styles.phaseProgress}>
          <ProgressBar 
            progress={phase.progress} 
            compact={true}
            color={statusColors[phase.status]}
          />
          <span className={styles.progressPercent}>{phase.progress}%</span>
        </div>

        <button className={styles.toggleBtn}>
          {isExpanded ? '▼' : '▶'}
        </button>
      </div>

      {/* Phase Agents (Expanded) */}
      {isExpanded && (
        <div className={styles.agentsContainer}>
          {phase.agents.length === 0 ? (
            <div className={styles.emptyAgents}>No agents in this phase</div>
          ) : (
            phase.agents.map((agent, idx) => (
              <AgentCard 
                key={agent.id || idx} 
                agent={agent}
                phaseId={phase.id}
              />
            ))
          )}
        </div>
      )}
    </div>
  );
}

// frontend/src/components/orchestration/AgentCard.jsx
import React, { useState } from 'react';
import styles from './orchestration.module.css';

export default function AgentCard({ agent, phaseId }) {
  const [expanded, setExpanded] = useState(false);

  const statusStyles = {
    'running': { bg: '#e8f5e9', border: '#4CAF50', icon: '⚙️' },
    'complete': { bg: '#f1f8f4', border: '#28A745', icon: '✓' },
    'error': { bg: '#ffebee', border: '#f44336', icon: '✕' },
    'queued': { bg: '#f5f5f5', border: '#9E9E9E', icon: '⧖' }
  };

  const style = statusStyles[agent.status] || statusStyles.queued;

  return (
    <div 
      className={styles.agentCard}
      style={{ 
        backgroundColor: style.bg,
        borderLeftColor: style.border
      }}
    >
      <div className={styles.agentCardHeader} onClick={() => setExpanded(!expanded)}>
        <span className={styles.agentIcon}>{style.icon}</span>
        
        <div className={styles.agentInfo}>
          <h4>{agent.name}</h4>
          <p className={styles.agentStatus}>{agent.status}</p>
        </div>

        {agent.error && (
          <div className={styles.agentError}>
            {agent.error.substring(0, 50)}...
          </div>
        )}

        {expanded && (
          <button className={styles.expandBtn}>▼</button>
        )}
      </div>

      {expanded && agent.output && (
        <div className={styles.agentOutput}>
          <pre>{agent.output}</pre>
        </div>
      )}
    </div>
  );
}

// frontend/src/components/orchestration/ProgressBar.jsx
import React from 'react';
import styles from './orchestration.module.css';

export default function ProgressBar({ progress, compact = false, color = '#007BFF' }) {
  return (
    <div className={`${styles.progressBar} ${compact ? styles.compact : ''}`}>
      <div 
        className={styles.progressFill}
        style={{
          width: `${Math.min(progress, 100)}%`,
          backgroundColor: color,
          transition: 'width 0.3s ease'
        }}
      ></div>
    </div>
  );
}

// frontend/src/components/orchestration/LiveLog.jsx
import React, { useEffect, useRef } from 'react';
import styles from './orchestration.module.css';

export default function LiveLog({ logs, isRunning, autoScroll, onAutoScrollToggle }) {
  const logRef = useRef(null);

  useEffect(() => {
    if (autoScroll && logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  const levelStyles = {
    'info': { color: '#0066CC', symbol: 'ℹ️' },
    'success': { color: '#00AA00', symbol: '✓' },
    'error': { color: '#CC0000', symbol: '✕' },
    'warning': { color: '#FF9900', symbol: '⚠️' }
  };

  return (
    <div className={styles.liveLogContainer}>
      <div className={styles.logHeader}>
        <h3>Live Log</h3>
        <div className={styles.logControls}>
          <label>
            <input 
              type="checkbox" 
              checked={autoScroll}
              onChange={onAutoScrollToggle}
            />
            Auto-scroll
          </label>
        </div>
      </div>

      <div className={styles.liveLog} ref={logRef}>
        {logs.length === 0 ? (
          <p className={styles.noLogs}>Waiting for build to start...</p>
        ) : (
          logs.map((log, idx) => (
            <div 
              key={idx}
              className={styles.logLine}
              style={{ borderLeftColor: levelStyles[log.level]?.color }}
            >
              <span className={styles.logTime}>
                {log.timestamp?.toLocaleTimeString()}
              </span>
              <span className={styles.logLevel}>
                {levelStyles[log.level]?.symbol}
              </span>
              <span className={styles.logAgent}>
                {log.agent}:
              </span>
              <span className={styles.logMessage}>
                {log.message}
              </span>
            </div>
          ))
        )}
        {isRunning && (
          <div className={styles.logLine} style={{ opacity: 0.5 }}>
            <span className={styles.spinner}>⠋</span> Running...
          </div>
        )}
      </div>
    </div>
  );
}

// frontend/src/components/orchestration/orchestration.module.css
.kanbanContainer {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 24px;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  min-height: 100vh;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  border-bottom: 3px solid #007BFF;
}

.headerLeft h1 {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  color: #212529;
}

.jobId {
  font-size: 14px;
  color: #6C757D;
  margin-left: 12px;
  font-family: 'Monaco', 'Menlo', monospace;
}

.headerRight {
  display: flex;
  align-items: center;
  gap: 24px;
}

.status {
  display: flex;
  align-items: center;
  gap: 12px;
}

.statusRunning {
  color: #28A745;
  font-weight: 600;
}

.statusComplete {
  color: #007BFF;
  font-weight: 600;
}

.progressText {
  font-weight: 700;
  color: #212529;
  min-width: 50px;
}

.phasesContainer {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 16px;
}

.phaseGroup {
  background: white;
  border-radius: 8px;
  border-left: 4px solid #6C757D;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

.phaseGroup.expanded {
  grid-column: 1 / -1;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.phaseHeader {
  padding: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  background: #f8f9fa;
  border-bottom: 1px solid #dee2e6;
  transition: background 0.2s;
}

.phaseHeader:hover {
  background: #f1f3f5;
}

.phaseTitle {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.phaseTitle h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #212529;
}

.phaseStats {
  font-size: 12px;
  color: #6C757D;
  background: #e9ecef;
  padding: 2px 8px;
  border-radius: 4px;
}

.statusIcon {
  font-size: 18px;
  font-weight: 700;
}

.phaseProgress {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 150px;
}

.progressPercent {
  font-weight: 600;
  color: #212529;
  min-width: 35px;
}

.toggleBtn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 16px;
  padding: 4px 8px;
}

.agentsContainer {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 600px;
  overflow-y: auto;
}

.emptyAgents {
  text-align: center;
  color: #6C757D;
  padding: 24px;
  font-style: italic;
}

.agentCard {
  background: #f9f9f9;
  border: 1px solid #ddd;
  border-left: 3px solid #007BFF;
  border-radius: 6px;
  padding: 12px;
  transition: all 0.2s;
}

.agentCard:hover {
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
}

.agentCardHeader {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
}

.agentIcon {
  font-size: 16px;
  min-width: 20px;
}

.agentInfo {
  flex: 1;
}

.agentInfo h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #212529;
}

.agentStatus {
  margin: 2px 0 0;
  font-size: 12px;
  color: #6C757D;
}

.agentError {
  flex: 1;
  font-size: 12px;
  color: #DC3545;
  background: #ffe6e6;
  padding: 6px 10px;
  border-radius: 4px;
  font-family: 'Monaco', 'Menlo', monospace;
}

.agentOutput {
  margin-top: 12px;
  padding: 12px;
  background: #1e1e1e;
  color: #00ff00;
  border-radius: 4px;
  overflow-x: auto;
  font-size: 11px;
  line-height: 1.4;
  font-family: 'Monaco', 'Menlo', monospace;
  max-height: 300px;
  overflow-y: auto;
}

.agentOutput pre {
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.expandBtn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 12px;
}

.progressBar {
  width: 100%;
  height: 24px;
  background: #e9ecef;
  border-radius: 4px;
  overflow: hidden;
}

.progressBar.compact {
  height: 16px;
}

.progressFill {
  height: 100%;
  background: #007BFF;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 11px;
  font-weight: 600;
  transition: width 0.3s ease;
}

.liveLogContainer {
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  height: 400px;
}

.logHeader {
  padding: 16px;
  border-bottom: 1px solid #dee2e6;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logHeader h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.logControls {
  display: flex;
  gap: 12px;
  align-items: center;
}

.logControls label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  cursor: pointer;
}

.logControls input {
  cursor: pointer;
}

.liveLog {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 12px;
  line-height: 1.5;
  background: #1e1e1e;
}

.logLine {
  display: flex;
  gap: 8px;
  padding: 4px 0;
  border-left: 2px solid #444;
  padding-left: 8px;
  color: #00ff00;
}

.logTime {
  color: #888;
  min-width: 70px;
}

.logLevel {
  min-width: 20px;
}

.logAgent {
  color: #FFD700;
  min-width: 120px;
  font-weight: 600;
}

.logMessage {
  flex: 1;
  word-break: break-word;
}

.noLogs {
  text-align: center;
  color: #888;
  padding: 40px 20px;
  font-style: italic;
}

.spinner {
  display: inline-block;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error {
  padding: 40px;
  background: white;
  border-radius: 8px;
  text-align: center;
  color: #DC3545;
}

.error h2 {
  margin-top: 0;
}

.error button {
  padding: 10px 20px;
  background: #007BFF;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.error button:hover {
  background: #0056B3;
}

.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 400px;
  color: #6C757D;
}

.emptyState {
  text-align: center;
  padding: 60px 20px;
  color: #6C757D;
}

@media (max-width: 768px) {
  .kanbanContainer {
    padding: 16px;
    gap: 16px;
  }

  .header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .headerRight {
    width: 100%;
    flex-direction: column;
  }

  .phasesContainer {
    grid-template-columns: 1fr;
  }

  .phaseHeader {
    flex-wrap: wrap;
  }

  .liveLogContainer {
    height: 300px;
  }
}
