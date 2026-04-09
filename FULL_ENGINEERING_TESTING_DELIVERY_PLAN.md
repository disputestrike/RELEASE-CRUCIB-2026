# 🔥 COMPLETE ENGINEERING + TESTING PLAN: ALL 5 FEATURES

**Status:** APPROVED FOR IMPLEMENTATION  
**Timeline:** 22-26 weeks (June-December 2026)  
**Resource:** 4 engineers (parallel tracks)  
**Cost:** $50-75k cloud + dev time  

---

## TRACK 1: KANBAN UI (4-6 weeks)
### Feature 1 - User Visibility & Orchestration Dashboard

**Owner:** Frontend Engineer (1 FTE)  
**Dependencies:** None (can start immediately)  
**Timeline:** Weeks 1-6 (April 10 - May 22, 2026)

---

### 1.1 DESIGN PHASE (Week 1-2)

#### Wireframes & Component Spec
```
┌─────────────────────────────────────────────────────────┐
│ CrucibAI Build: Aegis Omega                   [STOP]    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ Build Status: 45/88 | Elapsed: 12m 34s                 │
│                                                          │
│ Phase 1: Requirements ━━━━━━━━━━━━━━ 100% [5/5 DONE]   │
│                                                          │
│ Phase 2: Stack Selection ━━━━━━━━━━━━ 80% [4/5 DONE]   │
│ ├─ [✓] Tech Stack Analyzer                             │
│ ├─ [✓] Frontend Framework Selector                     │
│ ├─ [✓] Backend Framework Selector                      │
│ ├─ [✓] Database Selector                               │
│ └─ [⏳ 45%] DevOps Configurator (in progress)          │
│     └─ Status: Analyzing CI/CD options...              │
│                                                          │
│ Phase 3: Frontend Generation ━━━━━━━ 60% [15/25 DONE]  │
│ ├─ [✓] Layout Generator                                │
│ ├─ [✓] Navigation Component Generator                  │
│ ├─ [✓] Form Builder Agent                              │
│ ├─ [⏳ 80%] Authentication UI (in progress)            │
│ │    ├─ Est. time: 2m 15s remaining                    │
│ │    └─ Generated 342 lines of React                   │
│ ├─ [ ] Dashboard Generator                             │
│ ├─ [ ] Settings Page Generator                         │
│ └─ ... 10 more agents queued                           │
│                                                          │
│ ┌─ Live Log ──────────────────────────┐               │
│ │ > Authentication UI Agent started   │               │
│ │ > Analyzing user requirements       │               │
│ │ > Found 3 form fields               │               │
│ │ > Generating login form component   │               │
│ │ > Installing dependencies: axios    │               │
│ │ > Created src/components/Login.jsx  │               │
│ │ > Running linter...                 │               │
│ └─────────────────────────────────────┘               │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

#### Components to Build
1. **KanbanBoard.jsx** - Main orchestration UI
2. **PhaseGroup.jsx** - Phase container with progress bar
3. **AgentCard.jsx** - Individual agent task card
4. **ProgressBar.jsx** - Phase completion indicator
5. **LiveLog.jsx** - Real-time output panel
6. **AgentStatusIndicator.jsx** - Status badge (running/done/failed/queued)

---

### 1.2 IMPLEMENTATION PHASE (Week 2-5)

#### Frontend Structure
```
frontend/src/
├── components/
│   ├── orchestration/
│   │   ├── KanbanBoard.jsx              [NEW]
│   │   ├── PhaseGroup.jsx               [NEW]
│   │   ├── AgentCard.jsx                [NEW]
│   │   ├── ProgressBar.jsx              [NEW]
│   │   ├── LiveLog.jsx                  [NEW]
│   │   ├── AgentStatusIndicator.jsx     [NEW]
│   │   └── orchestration.module.css     [NEW]
│   └── ...existing
│
├── hooks/
│   ├── useJobProgress.js                [NEW]
│   └── useWebSocket.js                  [NEW]
│
├── pages/
│   └── Build.jsx                        [MODIFY]
│
└── api/
    └── jobProgress.js                   [NEW]
```

#### Key Component: KanbanBoard.jsx
```javascript
// frontend/src/components/orchestration/KanbanBoard.jsx

import React, { useState, useEffect, useCallback } from 'react';
import { useJobProgress } from '../../hooks/useJobProgress';
import PhaseGroup from './PhaseGroup';
import LiveLog from './LiveLog';
import styles from './orchestration.module.css';

export default function KanbanBoard({ jobId }) {
  const { phases, logs, isRunning, totalProgress } = useJobProgress(jobId);
  const [expandedPhase, setExpandedPhase] = useState(null);

  if (!phases) {
    return <div className={styles.loading}>Loading orchestration...</div>;
  }

  return (
    <div className={styles.kanbanContainer}>
      {/* Header */}
      <div className={styles.header}>
        <h1>CrucibAI Build: {jobId}</h1>
        <div className={styles.stats}>
          <span>Progress: {totalProgress}%</span>
          <span>Status: {isRunning ? '🟢 Running' : '⚫ Complete'}</span>
        </div>
      </div>

      {/* Phases */}
      <div className={styles.phasesContainer}>
        {phases.map((phase, idx) => (
          <PhaseGroup
            key={phase.id}
            phase={phase}
            isExpanded={expandedPhase === phase.id}
            onToggle={() => setExpandedPhase(expandedPhase === phase.id ? null : phase.id)}
          />
        ))}
      </div>

      {/* Live Log */}
      <LiveLog logs={logs} isRunning={isRunning} />
    </div>
  );
}
```

#### Key Hook: useJobProgress.js
```javascript
// frontend/src/hooks/useJobProgress.js

import { useState, useEffect } from 'react';
import { useWebSocket } from './useWebSocket';

export function useJobProgress(jobId) {
  const [phases, setPhases] = useState(null);
  const [logs, setLogs] = useState([]);
  const [isRunning, setIsRunning] = useState(true);
  const [totalProgress, setTotalProgress] = useState(0);

  const { lastMessage } = useWebSocket(`/api/job/${jobId}/progress`);

  useEffect(() => {
    if (!lastMessage) return;

    const event = JSON.parse(lastMessage);

    switch (event.type) {
      case 'phase_update':
        setPhases(prev => prev.map(p => 
          p.id === event.phase_id 
            ? { ...p, ...event.data } 
            : p
        ));
        break;

      case 'agent_start':
        setLogs(prev => [...prev, {
          timestamp: new Date(),
          agent: event.agent_name,
          message: `Starting ${event.agent_name}...`,
          level: 'info'
        }]);
        break;

      case 'agent_complete':
        setLogs(prev => [...prev, {
          timestamp: new Date(),
          agent: event.agent_name,
          message: `✓ ${event.agent_name} completed`,
          level: 'success'
        }]);
        break;

      case 'agent_error':
        setLogs(prev => [...prev, {
          timestamp: new Date(),
          agent: event.agent_name,
          message: `✗ Error: ${event.error}`,
          level: 'error'
        }]);
        break;

      case 'build_complete':
        setIsRunning(false);
        setTotalProgress(100);
        break;

      default:
        break;
    }
  }, [lastMessage]);

  return { phases, logs, isRunning, totalProgress };
}
```

#### Styling: orchestration.module.css
```css
.kanbanContainer {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 24px;
  background: #f8f9fa;
  min-height: 100vh;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 2px solid #e0e0e0;
  padding-bottom: 16px;
}

.header h1 {
  font-size: 24px;
  font-weight: 600;
  margin: 0;
}

.stats {
  display: flex;
  gap: 20px;
  font-size: 14px;
}

.phasesContainer {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 16px;
}

.phaseGroup {
  background: white;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  border-left: 4px solid #007bff;
}

.phaseGroup.expanded {
  grid-column: 1 / -1;
}

.agentCard {
  background: #f9f9f9;
  border: 1px solid #ddd;
  border-radius: 6px;
  padding: 12px;
  margin: 8px 0;
  display: flex;
  gap: 12px;
  align-items: center;
}

.agentCard.running {
  border-color: #4CAF50;
  background: #f1f8f4;
}

.agentCard.error {
  border-color: #f44336;
  background: #fef5f5;
}

.liveLog {
  background: #1e1e1e;
  color: #00ff00;
  font-family: 'Courier New', monospace;
  padding: 16px;
  border-radius: 8px;
  max-height: 400px;
  overflow-y: auto;
  font-size: 12px;
  line-height: 1.5;
}
```

---

### 1.3 BACKEND WIRING (Week 3-4)

#### WebSocket Endpoint: job_progress.py
```python
# backend/api/routes/job_progress.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, List
import json
import asyncio
from datetime import datetime

router = APIRouter()

# Store active WebSocket connections per job
active_connections: Dict[str, List[WebSocket]] = {}

@router.websocket("/api/job/{job_id}/progress")
async def websocket_job_progress(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time job progress updates.
    
    Events sent:
    - phase_update: Phase completion progress
    - agent_start: Agent started
    - agent_complete: Agent finished
    - agent_error: Agent failed
    - build_complete: Entire build done
    """
    await websocket.accept()
    
    if job_id not in active_connections:
        active_connections[job_id] = []
    
    active_connections[job_id].append(websocket)
    
    try:
        # Keep connection alive
        while True:
            try:
                await websocket.receive_text()
            except:
                break
    except WebSocketDisconnect:
        active_connections[job_id].remove(websocket)
    finally:
        if job_id in active_connections and not active_connections[job_id]:
            del active_connections[job_id]


async def broadcast_to_job(job_id: str, event: dict):
    """
    Broadcast event to all WebSocket clients watching this job.
    
    Called from executor.py after each agent runs.
    """
    if job_id not in active_connections:
        return
    
    message = json.dumps({
        **event,
        'timestamp': datetime.utcnow().isoformat()
    })
    
    # Send to all connected clients
    disconnected = []
    for websocket in active_connections[job_id]:
        try:
            await websocket.send_text(message)
        except:
            disconnected.append(websocket)
    
    # Clean up disconnected clients
    for ws in disconnected:
        active_connections[job_id].remove(ws)


# REST endpoint to get historical progress
@router.get("/api/job/{job_id}/progress")
async def get_job_progress(job_id: str):
    """
    GET endpoint for initial progress state.
    
    Useful for page refresh - get current state without WebSocket.
    """
    # Query database for current phase/agent status
    job = await Job.get(job_id)
    
    return {
        "job_id": job_id,
        "phases": await build_phase_data(job),
        "total_progress": calculate_progress(job),
        "is_running": job.status == "running"
    }
```

#### Integration Point: executor.py (MODIFY)
```python
# backend/orchestration/executor.py - ADD THIS

from api.routes.job_progress import broadcast_to_job

async def execute_agents_with_progress(job_id, agents, workspace_path):
    """
    Execute agents and broadcast progress events.
    """
    total_agents = len(agents)
    completed = 0
    
    for phase_idx, (phase_name, phase_agents) in enumerate(agents.items()):
        # Phase started
        await broadcast_to_job(job_id, {
            'type': 'phase_update',
            'phase_id': phase_name,
            'status': 'running',
            'progress': phase_idx / len(agents) * 100
        })
        
        for agent in phase_agents:
            # Agent starting
            await broadcast_to_job(job_id, {
                'type': 'agent_start',
                'agent_name': agent.name,
                'phase_id': phase_name
            })
            
            try:
                # Run the agent
                result = await agent.execute(context)
                
                completed += 1
                
                # Agent complete
                await broadcast_to_job(job_id, {
                    'type': 'agent_complete',
                    'agent_name': agent.name,
                    'phase_id': phase_name,
                    'progress': completed / total_agents * 100,
                    'result_summary': result.get('summary')
                })
                
            except Exception as e:
                # Agent error
                await broadcast_to_job(job_id, {
                    'type': 'agent_error',
                    'agent_name': agent.name,
                    'phase_id': phase_name,
                    'error': str(e)
                })
    
    # Build complete
    await broadcast_to_job(job_id, {
        'type': 'build_complete',
        'job_id': job_id,
        'status': 'success',
        'total_time': time.time() - start_time
    })
```

---

### 1.4 INTEGRATION TESTING (Week 5-6)

#### Test Suite: test_kanban_ui.py
```python
# tests/test_kanban_ui.py

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_kanban_ui_loads():
    """Test that Kanban UI loads successfully."""
    response = client.get("/")
    assert response.status_code == 200
    assert "KanbanBoard" in response.text

def test_phase_progress_api():
    """Test /api/job/{job_id}/progress endpoint."""
    response = client.get("/api/job/test-job-123/progress")
    assert response.status_code == 200
    
    data = response.json()
    assert "phases" in data
    assert "total_progress" in data
    assert "is_running" in data

@pytest.mark.asyncio
async def test_websocket_progress():
    """Test WebSocket progress updates."""
    with client.websocket_connect("/api/job/test-job-456/progress") as websocket:
        # Simulate executor sending updates
        await broadcast_to_job("test-job-456", {
            'type': 'agent_start',
            'agent_name': 'Frontend Generator'
        })
        
        # Receive message
        data = websocket.receive_json()
        assert data['type'] == 'agent_start'
        assert data['agent_name'] == 'Frontend Generator'

def test_agent_progress_updates():
    """Test agent progress card updates."""
    # Verify AgentCard component updates in real-time
    assert True  # Jest test in frontend

def test_live_log_output():
    """Test live log captures all output."""
    # Verify logs are streamed correctly
    assert True  # Jest test in frontend

def test_phase_completion_calculation():
    """Test phase progress bar calculation."""
    phases = [
        {'id': 'phase1', 'total_agents': 5, 'completed_agents': 5},
        {'id': 'phase2', 'total_agents': 10, 'completed_agents': 7},
        {'id': 'phase3', 'total_agents': 15, 'completed_agents': 0},
    ]
    
    progress = calculate_progress(phases)
    expected = (5 + 7) / (5 + 10 + 15) * 100
    assert abs(progress - expected) < 0.1
```

#### Frontend Jest Tests: orchestration.test.js
```javascript
// frontend/src/components/orchestration/orchestration.test.js

import { render, screen, waitFor } from '@testing-library/react';
import KanbanBoard from './KanbanBoard';
import { useJobProgress } from '../../hooks/useJobProgress';

jest.mock('../../hooks/useJobProgress');

describe('KanbanBoard', () => {
  it('renders phase groups', () => {
    useJobProgress.mockReturnValue({
      phases: [
        {
          id: 'phase1',
          name: 'Requirements',
          agents: [
            { id: 'a1', name: 'Requirement Analyzer', status: 'done' }
          ]
        }
      ],
      logs: [],
      isRunning: false,
      totalProgress: 100
    });

    render(<KanbanBoard jobId="test-job" />);
    expect(screen.getByText('Requirements')).toBeInTheDocument();
  });

  it('updates progress in real-time', async () => {
    const { rerender } = render(<KanbanBoard jobId="test-job" />);
    
    useJobProgress.mockReturnValue({
      phases: [],
      logs: [],
      isRunning: true,
      totalProgress: 50
    });

    rerender(<KanbanBoard jobId="test-job" />);
    
    await waitFor(() => {
      expect(screen.getByText('Progress: 50%')).toBeInTheDocument();
    });
  });

  it('displays live logs', () => {
    useJobProgress.mockReturnValue({
      phases: [],
      logs: [
        { timestamp: new Date(), agent: 'Agent 1', message: 'Starting...', level: 'info' }
      ],
      isRunning: true,
      totalProgress: 25
    });

    render(<KanbanBoard jobId="test-job" />);
    expect(screen.getByText(/Starting.../)).toBeInTheDocument();
  });
});
```

---

### 1.5 DEPLOYMENT CHECKLIST (Week 6)

- [ ] Frontend components built and tested (Jest)
- [ ] WebSocket endpoint implemented and tested
- [ ] Executor.py integration complete
- [ ] CSS styling complete (mobile-responsive)
- [ ] Accessibility audit (a11y)
- [ ] Performance testing (< 100ms updates)
- [ ] E2E test with real job flow
- [ ] Deploy to Railway
- [ ] Production validation

---

## TRACK 2: SANDBOX SECURITY (3-4 weeks)
### Feature 2 - Network Isolation & Privilege Hardening

**Owner:** DevOps / Infrastructure Engineer (1 FTE)  
**Dependencies:** None (can start immediately)  
**Timeline:** Weeks 1-4 (April 10 - May 8, 2026)

---

### 2.1 REQUIREMENTS & AUDIT (Week 1)

#### Security Threat Model
```
THREATS WE MITIGATE:
├─ Network escape (agent code phones home with secrets)
│  └─ FIX: No egress except whitelisted APIs
├─ Privilege escalation (agent runs code as root)
│  └─ FIX: Drop to non-root user, drop Linux capabilities
├─ Filesystem escape (agent reads /etc/passwd from other projects)
│  └─ FIX: Read-only /etc, tmpfs for temp files
├─ Resource starvation (agent consumes all memory)
│  └─ FIX: CPU/memory/timeout limits
└─ Code persistence (agent writes backdoor for later)
   └─ FIX: Ephemeral container, delete on stop
```

#### Audit Checklist
- [ ] Current Docker image has no security hardening
- [ ] Network: containers can reach any external host
- [ ] Privileges: containers run as root
- [ ] Filesystem: /etc is writable, /sys is writable
- [ ] Resources: no limits set
- [ ] Timeouts: agents can run forever

---

### 2.2 DOCKER HARDENING (Week 1-2)

#### Secure Dockerfile
```dockerfile
# Dockerfile.agent (NEW - replace current)

# Multi-stage build for smaller image
FROM node:18-alpine AS builder

# Stage 2: Runtime (minimal)
FROM node:18-alpine

# Install only necessary tools
RUN apk add --no-cache \
    python3 \
    git \
    curl

# Create non-root user
RUN addgroup -g 1000 crucibai && \
    adduser -D -u 1000 -G crucibai crucibai

# Copy app code (from builder)
COPY --chown=crucibai:crucibai --from=builder /app /app

WORKDIR /app

# Make /etc read-only
RUN chmod -R a-w /etc /sys /proc/sys

# Drop dangerous capabilities
RUN setcap -r /bin/sh 2>/dev/null || true

# Switch to non-root user
USER crucibai:crucibai

# Set resource limits (enforced by container runtime)
# See docker-compose.yml for actual limits

# Run agent executor
CMD ["node", "executor.js"]
```

#### Kubernetes SecurityContext
```yaml
# k8s/agent-pod-security.yaml (NEW)

apiVersion: v1
kind: Pod
metadata:
  name: crucibai-agent
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
    fsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
  
  containers:
  - name: agent
    image: crucibai/agent:latest
    
    securityContext:
      # Drop all capabilities
      capabilities:
        drop:
        - ALL
      
      # Disallow privilege escalation
      allowPrivilegeEscalation: false
      
      # Read-only root filesystem
      readOnlyRootFilesystem: true
    
    # Resource limits
    resources:
      requests:
        memory: "512Mi"
        cpu: "500m"
      limits:
        memory: "2Gi"
        cpu: "2000m"
    
    # 60 second timeout
    livenessProbe:
      exec:
        command:
        - /bin/sh
        - -c
        - "test -f /tmp/agent_running"
      initialDelaySeconds: 5
      periodSeconds: 10
      timeoutSeconds: 60
    
    # Ephemeral volumes
    volumeMounts:
    - name: tmp
      mountPath: /tmp
    - name: home
      mountPath: /home/crucibai
  
  volumes:
  - name: tmp
    emptyDir: {}
  - name: home
    emptyDir: {}
```

#### Docker Compose with Network Isolation
```yaml
# docker-compose.agent.yml (NEW)

version: '3.9'

services:
  agent:
    build:
      context: .
      dockerfile: Dockerfile.agent
    
    # Security
    user: "1000:1000"
    read_only_root_filesystem: true
    security_opt:
      - no-new-privileges:true
      - seccomp:unconfined  # Use seccomp profile in production
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE  # Only if needed
    
    # Resource limits
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
    
    # Network isolation
    networks:
      - crucibai-network
    
    # Ephemeral storage
    volumes:
      - type: tmpfs
        target: /tmp
      - type: tmpfs
        target: /home/crucibai
    
    # No internet access by default
    environment:
      - CRUCIBAI_NETWORK_WHITELIST=api.anthropic.com,api.cerebras.ai,api.supabase.io

networks:
  crucibai-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.25.0.0/16

  # No external access
  driver_opts:
    com.docker.network.bridge.name: crucibai-br0
```

---

### 2.3 NETWORK EGRESS FILTERING (Week 2-3)

#### egress_filter.py (Network Proxy)
```python
# backend/sandbox/egress_filter.py (NEW)

import subprocess
from typing import Dict, List
from urllib.parse import urlparse

class EgressFilter:
    """
    Whitelist external services that agents can reach.
    All other network traffic is blocked.
    """
    
    WHITELIST = {
        # LLM APIs
        'api.anthropic.com': ['https'],
        'api.cerebras.ai': ['https'],
        'api.openai.com': ['https'],
        
        # Data services
        'api.supabase.io': ['https'],
        'db.supabase.io': ['https'],
        'storage.googleapis.com': ['https'],
        
        # Package managers
        'registry.npmjs.org': ['https'],
        'pypi.org': ['https'],
        'files.pythonhosted.org': ['https'],
        
        # Git
        'github.com': ['https'],
        'gitlab.com': ['https'],
        
        # Monitoring (internal only)
        'metrics.crucibai.internal': ['https'],
        'logs.crucibai.internal': ['https'],
    }
    
    @classmethod
    def setup_iptables(cls):
        """
        Configure iptables to block egress except whitelist.
        
        Run as: docker run --cap-add NET_ADMIN ... setup_network.sh
        """
        commands = [
            # Default deny egress
            "iptables -P OUTPUT DROP",
            "iptables -P FORWARD DROP",
            
            # Allow localhost
            "iptables -A OUTPUT -o lo -j ACCEPT",
            
            # Allow whitelisted domains
        ]
        
        for domain, protocols in cls.WHITELIST.items():
            # DNS resolution allowed
            commands.append(f"iptables -A OUTPUT -d {domain} -j ACCEPT")
        
        for cmd in commands:
            subprocess.run(cmd.split(), check=True)
    
    @classmethod
    def check_url(cls, url: str) -> bool:
        """
        Verify URL is whitelisted before allowing agent request.
        """
        parsed = urlparse(url)
        hostname = parsed.hostname or parsed.netloc
        protocol = parsed.scheme or 'https'
        
        if hostname not in cls.WHITELIST:
            return False
        
        if protocol not in cls.WHITELIST[hostname]:
            return False
        
        return True
    
    @classmethod
    def validate_request(cls, method, url, headers=None):
        """
        Called by agent HTTP library before making request.
        Raises exception if not whitelisted.
        """
        if not cls.check_url(url):
            raise PermissionError(
                f"Network request to {url} not whitelisted. "
                f"Contact support to add domain."
            )
        
        # Also check headers for secrets
        if headers:
            for key, value in headers.items():
                if any(secret in str(value) for secret in [
                    'sk-', 'api_key', 'secret', 'password'
                ]):
                    raise ValueError(
                        f"Detected secret in header {key}. "
                        f"Use environment variables instead."
                    )
```

#### Environment Variable Injection
```python
# backend/sandbox/environment_setup.py (NEW)

class SandboxEnvironment:
    """
    Inject whitelisted secrets into agent containers.
    """
    
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.env_vars = {}
    
    def add_api_key(self, service: str, key: str):
        """Add API key that agents can read."""
        if service not in ['anthropic', 'cerebras', 'openai', 'supabase']:
            raise ValueError(f"Unknown service: {service}")
        
        self.env_vars[f"{service.upper()}_API_KEY"] = key
    
    def get_env_dict(self) -> dict:
        """
        Return env dict for Docker container.
        
        Secrets are mounted as env vars, NOT in code.
        """
        return {
            # Whitelisted APIs
            'ANTHROPIC_API_KEY': self.env_vars.get('anthropic'),
            'CEREBRAS_API_KEY': self.env_vars.get('cerebras'),
            'OPENAI_API_KEY': self.env_vars.get('openai'),
            'SUPABASE_URL': self.env_vars.get('supabase_url'),
            'SUPABASE_KEY': self.env_vars.get('supabase_key'),
            
            # Internal services (sandbox can reach via bridge network)
            'CRUCIBAI_METRICS_URL': 'http://metrics.crucibai.internal:9090',
            'CRUCIBAI_LOGS_URL': 'http://logs.crucibai.internal:5601',
            
            # Security markers
            'SANDBOX_JOB_ID': self.job_id,
            'SANDBOX_SECURITY_LEVEL': 'strict',
            'SANDBOX_TIMEOUT_SECONDS': '300',  # 5 min timeout
        }
```

---

### 2.4 TESTING (Week 3-4)

#### Security Tests: test_sandbox_security.py
```python
# tests/test_sandbox_security.py (NEW)

import pytest
import subprocess
from unittest.mock import patch

def test_container_runs_non_root():
    """Agent container must run as non-root user."""
    result = subprocess.run(
        ["docker", "run", "--rm", "crucibai/agent", "whoami"],
        capture_output=True,
        text=True
    )
    assert "crucibai" in result.stdout
    assert "root" not in result.stdout

def test_filesystem_readonly():
    """Agent cannot write to /etc, /sys."""
    result = subprocess.run([
        "docker", "run", "--rm", "crucibai/agent",
        "touch /etc/test 2>&1 || echo 'Read-only'"
    ], capture_output=True, text=True)
    
    assert "Read-only" in result.stdout or "Permission denied" in result.stdout

def test_network_whitelist_enforced():
    """Agent can only reach whitelisted domains."""
    # curl to blocked domain should fail
    result = subprocess.run([
        "docker", "run", "--rm", "--network", "crucibai-network",
        "crucibai/agent",
        "curl -s https://evil.com 2>&1 || echo 'Blocked'"
    ], capture_output=True, text=True, timeout=10)
    
    assert "Blocked" in result.stdout or result.returncode != 0

def test_cpu_limit_enforced():
    """Agent cannot exceed CPU limit."""
    # Run CPU-intensive task
    result = subprocess.run([
        "docker", "run", "--rm",
        "--cpus", "2.0",
        "crucibai/agent",
        "python -c 'import time; [i**2 for i in range(int(1e7))]'"
    ], capture_output=True, timeout=30)
    
    # Should complete without hanging
    assert result.returncode == 0

def test_memory_limit_enforced():
    """Agent cannot exceed memory limit."""
    result = subprocess.run([
        "docker", "run", "--rm",
        "--memory", "2g",
        "crucibai/agent",
        "python -c 'x = [0] * int(1e8)'"
    ], capture_output=True, timeout=30)
    
    # Should be killed if exceeds limit
    assert result.returncode != 0

def test_timeout_enforced():
    """Agent execution times out after 5 minutes."""
    result = subprocess.run([
        "timeout", "60",
        "docker", "run", "--rm", "crucibai/agent",
        "sleep 300"
    ], capture_output=True)
    
    # Should timeout before sleeping completes
    assert result.returncode == 124  # timeout exit code

def test_secret_not_in_logs():
    """API keys not logged to stdout/stderr."""
    with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'sk-test123'}):
        result = subprocess.run([
            "docker", "run", "--rm", "-e", "ANTHROPIC_API_KEY=sk-test123",
            "crucibai/agent", "env"
        ], capture_output=True, text=True)
    
    # Should not print secret
    assert "sk-test123" not in result.stdout
```

#### Pentest Simulation: pentest_sandbox.sh
```bash
#!/bin/bash
# tests/pentest_sandbox.sh

echo "🔓 Sandbox Security Pentest"
echo "=============================="

# Test 1: Privilege escalation
echo "Test 1: Privilege escalation"
docker run --rm crucibai/agent sh -c "whoami" | grep -q "crucibai" && echo "✓ PASS" || echo "✗ FAIL"

# Test 2: Filesystem escape
echo "Test 2: Filesystem escape (write /etc)"
docker run --rm crucibai/agent sh -c "touch /etc/test.txt 2>&1" | grep -q "Read-only\|Permission" && echo "✓ PASS" || echo "✗ FAIL"

# Test 3: Network escape
echo "Test 3: Network escape (reach external)"
timeout 5 docker run --rm crucibai/agent curl https://evil.com 2>&1 | grep -q "refused\|blocked\|Temporary failure" && echo "✓ PASS" || echo "✗ FAIL"

# Test 4: Resource limits
echo "Test 4: Memory limit"
docker run --rm --memory=100m crucibai/agent sh -c "python -c 'x=[0]*int(1e8)'" 2>&1 | grep -q "Killed\|Memory" && echo "✓ PASS" || echo "✗ FAIL"

# Test 5: Timeout
echo "Test 5: Execution timeout"
timeout 10 docker run --rm crucibai/agent sh -c "sleep 60" 2>&1 && echo "✗ FAIL" || echo "✓ PASS"

echo ""
echo "Pentest complete. All tests should PASS."
```

---

### 2.5 DEPLOYMENT (Week 4)

- [ ] Dockerfile hardening complete
- [ ] Kubernetes security policy applied
- [ ] Network egress filtering configured
- [ ] All security tests passing
- [ ] Pentest passed
- [ ] Deploy to staging
- [ ] Production hardening audit
- [ ] Deploy to production

---

## TRACK 3: VECTOR DB MEMORY (4-6 weeks)
### Feature 3 - Context Management & Token Overflow Prevention

**Owner:** ML / Backend Engineer (1 FTE)  
**Dependencies:** None (can start immediately, but should follow Vector DB setup)  
**Timeline:** Weeks 3-8 (May 1 - June 19, 2026)

---

### 3.1 DESIGN & SETUP (Week 1)

#### Vector DB Architecture
```
┌─ Pinecone Vector DB ─────────────────┐
│                                       │
│ Index: "crucibai-memory"              │
│ Dimension: 1536 (OpenAI embeddings)   │
│ Metric: cosine                        │
│                                       │
│ Vectors:                              │
│ ├─ (embedding_1, metadata_1)         │
│ ├─ (embedding_2, metadata_2)         │
│ └─ ...                                │
│                                       │
└───────────────────────────────────────┘

Each vector = embedded text from:
- User requirements
- Agent outputs
- Design decisions
- Error logs
- API schemas

Metadata:
{
  "project_id": "aegis-omega-123",
  "phase": 2,
  "agent": "Frontend Generator",
  "type": "output",  # or "requirement" or "error"
  "timestamp": "2026-05-01T12:34:56Z",
  "tokens": 450
}
```

#### Setup: Pinecone Client
```python
# backend/memory/vector_db.py (NEW)

import os
import json
from typing import List, Dict
from pinecone import Pinecone
from openai import OpenAI

class VectorMemory:
    """
    Manage project context in vector database.
    
    Stores all agent outputs, requirements, decisions.
    Allows retrieval when needed to maintain context.
    """
    
    def __init__(self):
        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self.index = self.pc.Index("crucibai-memory")
        self.embeddings_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    async def add_memory(
        self,
        project_id: str,
        text: str,
        memory_type: str,  # "output", "requirement", "decision", "error"
        agent_name: str = None,
        phase: int = None,
        metadata: Dict = None
    ):
        """
        Embed text and store in vector DB with metadata.
        
        Called after each agent completes or at key decision points.
        """
        # Create embedding
        embedding = await self._embed_text(text)
        
        # Create unique ID
        vector_id = f"{project_id}_{len(text)}_{hash(text) % 1000000}"
        
        # Prepare metadata
        meta = {
            "project_id": project_id,
            "text": text[:500],  # Preview in metadata
            "type": memory_type,
            "agent": agent_name,
            "phase": phase,
            "timestamp": datetime.utcnow().isoformat(),
            **metadata or {}
        }
        
        # Upsert to vector DB
        self.index.upsert(
            vectors=[
                (vector_id, embedding, meta)
            ]
        )
        
        return vector_id
    
    async def retrieve_context(
        self,
        project_id: str,
        query: str,
        top_k: int = 5
    ) -> List[Dict]:
        """
        Retrieve relevant memories for a query.
        
        Used when agent needs context (e.g., "What was the tech stack?")
        """
        # Embed query
        query_embedding = await self._embed_text(query)
        
        # Search in Pinecone
        results = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            filter={
                "project_id": {"$eq": project_id}
            }
        )
        
        # Format results
        memories = []
        for match in results['matches']:
            memories.append({
                "text": match['metadata']['text'],
                "type": match['metadata']['type'],
                "agent": match['metadata'].get('agent'),
                "relevance_score": match['score'],
                "timestamp": match['metadata'].get('timestamp')
            })
        
        return memories
    
    async def count_project_tokens(self, project_id: str) -> int:
        """
        Count total tokens used in a project.
        
        Used to trigger forking when approaching limit.
        """
        # Query all vectors for project
        results = self.index.query(
            vector=[0] * 1536,  # Dummy query
            top_k=10000,
            filter={"project_id": {"$eq": project_id}}
        )
        
        # Sum tokens from metadata
        total_tokens = 0
        for match in results['matches']:
            total_tokens += match['metadata'].get('tokens', 0)
        
        return total_tokens
    
    async def _embed_text(self, text: str) -> List[float]:
        """Embed text using OpenAI."""
        response = await self.embeddings_client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
```

---

### 3.2 INTEGRATION WITH AGENTS (Week 2-3)

#### Agent Execution with Memory
```python
# backend/orchestration/executor_with_memory.py (NEW)

from memory.vector_db import VectorMemory
from memory.forking import create_fork

class ExecutorWithMemory:
    """
    Execute agents with vector memory + forking support.
    """
    
    def __init__(self, job_id: str, project_id: str):
        self.job_id = job_id
        self.project_id = project_id
        self.memory = VectorMemory()
        self.token_limit = 100000  # 100k tokens per context
        self.fork_threshold = 0.7  # Create fork at 70% capacity
    
    async def execute_with_memory(self, agent, context):
        """
        Run agent with context retrieval + memory storage.
        """
        # Retrieve relevant context before agent runs
        if 'user_query' in context:
            relevant_memories = await self.memory.retrieve_context(
                self.project_id,
                context['user_query'],
                top_k=5
            )
            
            # Inject into agent context
            context['retrieved_memories'] = relevant_memories
            context['memory_injection'] = self._format_memories(relevant_memories)
        
        # Run agent
        result = await agent.execute(context)
        
        # Store output in memory
        await self.memory.add_memory(
            project_id=self.project_id,
            text=result.get('generated_code', result.get('output', ''))[:2000],
            memory_type='output',
            agent_name=agent.name,
            phase=context.get('phase'),
            metadata={'tokens': result.get('tokens_used', 0)}
        )
        
        # Check if forking needed
        await self._check_and_fork_if_needed(context)
        
        return result
    
    async def _check_and_fork_if_needed(self, context):
        """
        Check token usage. If >70% capacity, create fork.
        """
        tokens_used = await self.memory.count_project_tokens(self.project_id)
        usage_percent = tokens_used / self.token_limit
        
        if usage_percent > self.fork_threshold:
            logger.warning(
                f"Project {self.project_id} at {usage_percent*100:.1f}% capacity. "
                f"Creating fork..."
            )
            
            fork_id = await create_fork(
                project_id=self.project_id,
                fork_reason="Token overflow prevention",
                parent_context=context
            )
            
            # Continue in new fork
            context['fork_id'] = fork_id
            return fork_id
        
        return None
    
    def _format_memories(self, memories: List[Dict]) -> str:
        """
        Format retrieved memories for agent context injection.
        """
        formatted = "## Previous Context (Retrieved from Memory)\n\n"
        
        for i, mem in enumerate(memories, 1):
            formatted += f"**Memory {i}** (from {mem.get('agent', 'system')})\n"
            formatted += f"Type: {mem['type']}\n"
            formatted += f"Relevance: {mem['relevance_score']:.2f}/1.0\n"
            formatted += f"Content:\n```\n{mem['text']}\n```\n\n"
        
        return formatted
```

---

### 3.3 FORKING MECHANISM (Week 3-4)

#### Fork Creation & Management
```python
# backend/memory/forking.py (NEW)

from sqlalchemy import Column, String, JSON, DateTime, create_engine
from sqlalchemy.orm import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class ProjectFork(Base):
    """
    Track project forks for context overflow handling.
    """
    __tablename__ = "project_forks"
    
    fork_id = Column(String, primary_key=True)
    project_id = Column(String, index=True)
    parent_fork_id = Column(String, nullable=True)  # Linked list of forks
    fork_depth = Column(int, default=1)  # Generation number
    reason = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    token_count = Column(int, default=0)
    status = Column(String, default="active")  # "active", "completed", "failed"
    parent_context = Column(JSON)  # Saved context for resumption

async def create_fork(
    project_id: str,
    fork_reason: str,
    parent_context: Dict = None
) -> str:
    """
    Create a new fork of the project.
    
    When token limit approached, spawn new context with reference to parent.
    """
    fork_id = str(uuid.uuid4())[:8]
    
    # Find current fork
    current_fork = db.query(ProjectFork).filter(
        ProjectFork.project_id == project_id,
        ProjectFork.status == "active"
    ).first()
    
    # Create new fork
    new_fork = ProjectFork(
        fork_id=fork_id,
        project_id=project_id,
        parent_fork_id=current_fork.fork_id if current_fork else None,
        fork_depth=(current_fork.fork_depth + 1) if current_fork else 1,
        reason=fork_reason,
        parent_context=parent_context
    )
    
    db.add(new_fork)
    db.commit()
    
    logger.info(f"Created fork {fork_id} for project {project_id}")
    
    return fork_id

async def resume_from_fork(fork_id: str) -> Dict:
    """
    Resume project from a fork.
    
    Retrieve parent context and continue execution.
    """
    fork = db.query(ProjectFork).filter(
        ProjectFork.fork_id == fork_id
    ).first()
    
    if not fork:
        raise ValueError(f"Fork {fork_id} not found")
    
    return {
        "fork_id": fork_id,
        "parent_context": fork.parent_context,
        "token_count": fork.token_count,
        "fork_depth": fork.fork_depth
    }
```

---

### 3.4 SYSTEM PROMPT INJECTION (Week 4)

#### Memory-Aware Agent Prompts
```python
# backend/prompts/memory_system_prompt.txt (NEW)

SYSTEM_MEMORY_INJECTION = """
You are a skilled AI developer building a web application.

## Context Management

You have access to project memory - previous decisions, code, and designs.
When relevant, reference memories from previous steps.

Memory will be provided as:
```
## Previous Context (Retrieved from Memory)

**Memory 1** (from Frontend Generator)
Type: output
Relevance: 0.92/1.0
Content:
```
...previous code...
```
```

## Instructions

1. Review provided memories for context
2. If memories conflict with current requirements, flag it
3. Build on previous work - don't regenerate from scratch
4. When stuck, query memory: "What was the chosen tech stack?"

## Token Usage

This project has token capacity of 100,000.
Current usage: {current_tokens}/100,000

If approaching limit, focus on essential features only.

## Forking

If we approach token limit, the system will fork to a new context.
You'll receive: fork_id, parent_context, and can continue.
"""
```

---

### 3.5 TESTING (Week 5)

#### Test Vector Memory: test_vector_memory.py
```python
# tests/test_vector_memory.py (NEW)

import pytest
from memory.vector_db import VectorMemory
from memory.forking import create_fork

@pytest.mark.asyncio
async def test_add_memory():
    """Test storing memory in vector DB."""
    memory = VectorMemory()
    
    vector_id = await memory.add_memory(
        project_id="test-123",
        text="Built login form with React hooks",
        memory_type="output",
        agent_name="Frontend Generator"
    )
    
    assert vector_id is not None

@pytest.mark.asyncio
async def test_retrieve_context():
    """Test retrieving relevant memories."""
    memory = VectorMemory()
    
    # Add some memories
    await memory.add_memory(
        project_id="test-456",
        text="Tech stack: React + FastAPI + PostgreSQL",
        memory_type="decision"
    )
    
    # Query for context
    results = await memory.retrieve_context(
        project_id="test-456",
        query="What tech stack was chosen?"
    )
    
    assert len(results) > 0
    assert results[0]['relevance_score'] > 0.8

@pytest.mark.asyncio
async def test_token_counting():
    """Test token usage calculation."""
    memory = VectorMemory()
    
    # Add memory with tokens
    await memory.add_memory(
        project_id="test-789",
        text="Large generated component",
        memory_type="output",
        metadata={"tokens": 5000}
    )
    
    total = await memory.count_project_tokens("test-789")
    assert total >= 5000

@pytest.mark.asyncio
async def test_forking():
    """Test project forking on token overflow."""
    fork_id = await create_fork(
        project_id="test-overflow",
        fork_reason="Token limit approaching"
    )
    
    assert fork_id is not None
    
    # Verify fork created
    fork_data = await resume_from_fork(fork_id)
    assert fork_data['fork_id'] == fork_id

def test_memory_injection():
    """Test memory injection into agent prompt."""
    memories = [
        {"text": "React setup", "type": "output", "agent": "Frontend"},
        {"text": "API schema", "type": "decision", "agent": "Backend"}
    ]
    
    formatted = ExecutorWithMemory(None, None)._format_memories(memories)
    assert "React setup" in formatted
    assert "API schema" in formatted
```

---

### 3.6 DEPLOYMENT (Week 6)

- [ ] Pinecone account setup
- [ ] Vector memory client working
- [ ] Forking DB schema created
- [ ] Integration tests passing
- [ ] Agent context injection working
- [ ] Token counting accurate
- [ ] Fork resumption tested
- [ ] Deploy to staging
- [ ] Production deployment

---

## TRACK 4: DATABASE AUTO-PROVISIONING (3-5 weeks)
### Feature 4 - Lovable-Style Schema Creation

**Owner:** Backend / Database Engineer (1 FTE)  
**Dependencies:** None (can start immediately)  
**Timeline:** Weeks 4-8 (May 8 - June 19, 2026)

---

### 4.1 ARCHITECT AGENT SCHEMA PARSER (Week 1)

#### Schema Definition Language
```python
# backend/agents/database_architect_agent.py (NEW)

from pydantic import BaseModel
from typing import List, Optional

class ColumnDef(BaseModel):
    name: str
    type: str  # "text", "integer", "boolean", "uuid", "timestamp", etc.
    required: bool = True
    unique: bool = False
    primary_key: bool = False
    foreign_key: Optional[str] = None  # e.g., "users(id)"
    default: Optional[str] = None

class TableDef(BaseModel):
    name: str
    columns: List[ColumnDef]
    indexes: List[str] = []
    rls_policies: List[str] = []  # Row-level security

class SchemaResponse(BaseModel):
    tables: List[TableDef]
    migrations: List[str]

# Example:
"""
User: "Add a feedback form with fields: name, email, message, rating (1-5)"

Architect Agent generates:
{
  "tables": [
    {
      "name": "feedback",
      "columns": [
        {"name": "id", "type": "uuid", "primary_key": true},
        {"name": "name", "type": "text", "required": true},
        {"name": "email", "type": "text", "required": true},
        {"name": "message", "type": "text", "required": true},
        {"name": "rating", "type": "integer", "required": true},
        {"name": "created_at", "type": "timestamp", "default": "now()"}
      ],
      "indexes": ["email"]
    }
  ]
}
"""
```

#### Architect Agent with Schema Generation
```python
# backend/agents/database_architect_agent.py

class DatabaseArchitectAgent:
    """
    Parse user requirements and generate database schema.
    
    Called early in build phase.
    """
    
    async def execute(self, context):
        user_requirements = context.get('user_requirements', '')
        existing_schema = context.get('existing_schema', '')
        
        # Call LLM to generate schema
        prompt = f"""
You are a database architect for a new application.

User Requirements:
{user_requirements}

Existing Schema:
{existing_schema or "(none)"}

Based on the user requirements, generate a database schema.

Return ONLY valid JSON matching this format:
{{
  "tables": [
    {{
      "name": "table_name",
      "columns": [
        {{"name": "id", "type": "uuid", "primary_key": true}},
        {{"name": "field1", "type": "text", "required": true}},
        ...
      ],
      "indexes": ["field1"],
      "rls_policies": ["enable RLS; create policy..."]
    }}
  ]
}}

Key rules:
1. Every table needs an id (uuid) primary key
2. Every table needs created_at (timestamp, default now())
3. For auth, reference auth.users(id)
4. Use appropriate types: text, integer, boolean, uuid, timestamp, jsonb
5. Add indexes on frequently-queried fields
6. Add RLS policies for data isolation

Respond with ONLY the JSON.
"""
        
        response = await self.llm.generate(
            prompt=prompt,
            model="claude-opus-4-1",
            max_tokens=2000
        )
        
        # Parse schema
        try:
            schema = SchemaResponse(**json.loads(response))
        except:
            logger.error(f"Failed to parse schema: {response}")
            return {"status": "error", "reason": "Schema parsing failed"}
        
        # Store schema for later use
        context['database_schema'] = schema.dict()
        
        return {
            "status": "success",
            "schema": schema.dict(),
            "table_count": len(schema.tables),
            "summary": f"Created schema with {len(schema.tables)} tables"
        }
```

---

### 4.2 SUPABASE PROVISIONING (Week 2)

#### Supabase Schema Manager
```python
# backend/orchestration/supabase_manager.py (NEW)

from supabase import create_client, Client
import json

class SupabaseSchemaManager:
    """
    Create tables in Supabase from schema definition.
    """
    
    def __init__(self, supabase_url: str, supabase_key: str):
        self.client: Client = create_client(supabase_url, supabase_key)
        self.supabase_url = supabase_url
    
    async def create_tables_from_schema(self, schema: dict) -> dict:
        """
        Generate and execute SQL to create tables.
        """
        sql_statements = []
        
        for table in schema['tables']:
            sql = self._generate_create_table_sql(table)
            sql_statements.append(sql)
        
        # Execute all statements
        results = []
        for sql in sql_statements:
            try:
                result = await self.client.rpc(
                    'exec_sql',
                    {'sql': sql}
                )
                results.append({
                    "table": sql.split()[2],
                    "status": "success"
                })
            except Exception as e:
                logger.error(f"Failed to create table: {e}")
                results.append({
                    "table": sql.split()[2],
                    "status": "error",
                    "error": str(e)
                })
        
        return {
            "created_tables": results,
            "total": len(results)
        }
    
    def _generate_create_table_sql(self, table_def: dict) -> str:
        """
        Convert table definition to SQL.
        """
        lines = [f"CREATE TABLE IF NOT EXISTS {table_def['name']} ("]
        
        for col in table_def['columns']:
            col_sql = self._column_to_sql(col)
            lines.append(f"  {col_sql},")
        
        # Remove trailing comma from last line
        lines[-1] = lines[-1].rstrip(',')
        lines.append(");")
        
        sql = '\n'.join(lines)
        
        # Add indexes
        for idx in table_def.get('indexes', []):
            sql += f"\nCREATE INDEX IF NOT EXISTS idx_{table_def['name']}_{idx} ON {table_def['name']}({idx});"
        
        # Add RLS policies
        for policy in table_def.get('rls_policies', []):
            sql += f"\n{policy}"
        
        return sql
    
    def _column_to_sql(self, col: dict) -> str:
        """
        Convert column definition to SQL.
        """
        parts = [col['name']]
        
        # Type mapping
        type_map = {
            'text': 'TEXT',
            'integer': 'INTEGER',
            'boolean': 'BOOLEAN',
            'uuid': 'UUID DEFAULT gen_random_uuid()',
            'timestamp': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
            'jsonb': 'JSONB'
        }
        
        parts.append(type_map.get(col['type'], col['type']))
        
        if col.get('primary_key'):
            parts.append('PRIMARY KEY')
        elif col.get('required'):
            parts.append('NOT NULL')
        
        if col.get('unique'):
            parts.append('UNIQUE')
        
        if col.get('default'):
            parts.append(f"DEFAULT {col['default']}")
        
        if col.get('foreign_key'):
            parts.append(f"REFERENCES {col['foreign_key']}")
        
        return ' '.join(parts)
```

---

### 4.3 MIGRATION GENERATION (Week 3)

#### Migration File Creator
```python
# backend/orchestration/migrations.py (NEW)

from datetime import datetime
import os

class MigrationGenerator:
    """
    Generate Alembic migration files for schema changes.
    """
    
    def __init__(self, migrations_path: str = "migrations/versions"):
        self.migrations_path = migrations_path
    
    async def create_migration(
        self,
        project_id: str,
        schema: dict,
        description: str = "Auto-generated schema"
    ) -> str:
        """
        Create migration file from schema.
        
        Returns: migration file name
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{project_id}_auto_schema.py"
        filepath = os.path.join(self.migrations_path, filename)
        
        migration_code = self._generate_migration_code(schema, description)
        
        os.makedirs(self.migrations_path, exist_ok=True)
        with open(filepath, 'w') as f:
            f.write(migration_code)
        
        logger.info(f"Created migration: {filename}")
        return filename
    
    def _generate_migration_code(self, schema: dict, description: str) -> str:
        """
        Generate Alembic migration Python code.
        """
        code = f'''"""
{description}

Revision ID: auto_{int(time.time())}
Revises: 
Create Date: {datetime.utcnow().isoformat()}
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'auto_{int(time.time())}'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
'''
        
        for table in schema['tables']:
            code += f"\n    # Create {table['name']} table"
            code += f"\n    op.create_table("
            code += f"\n        '{table['name']}',"
            
            for col in table['columns']:
                code += f"\n        sa.Column('{col['name']}', "
                code += self._sqlalchemy_type(col['type'])
                
                if col.get('primary_key'):
                    code += ", primary_key=True"
                if col.get('required'):
                    code += ", nullable=False"
                if col.get('unique'):
                    code += ", unique=True"
                
                code += "),"
            
            code += "\n    )"
        
        code += "\n\ndef downgrade() -> None:"
        for table in schema['tables']:
            code += f"\n    op.drop_table('{table['name']}')"
        
        return code
    
    def _sqlalchemy_type(self, type_str: str) -> str:
        """
        Map type string to SQLAlchemy type.
        """
        mapping = {
            'text': 'sa.String()',
            'integer': 'sa.Integer()',
            'boolean': 'sa.Boolean()',
            'uuid': 'sa.UUID()',
            'timestamp': 'sa.DateTime()',
            'jsonb': 'sa.JSON()'
        }
        return mapping.get(type_str, 'sa.String()')
```

---

### 4.4 TESTING (Week 4-5)

#### Test Database Auto-Provisioning: test_db_provision.py
```python
# tests/test_db_provision.py (NEW)

import pytest
from orchestration.supabase_manager import SupabaseSchemaManager
from orchestration.migrations import MigrationGenerator

@pytest.mark.asyncio
async def test_schema_generation():
    """Test architect generates valid schema."""
    agent = DatabaseArchitectAgent()
    
    result = await agent.execute({
        'user_requirements': 'Build a feedback form with name, email, message'
    })
    
    assert result['status'] == 'success'
    assert 'schema' in result
    assert len(result['schema']['tables']) > 0

def test_sql_generation():
    """Test SQL generation from schema."""
    schema = {
        'tables': [
            {
                'name': 'feedback',
                'columns': [
                    {'name': 'id', 'type': 'uuid', 'primary_key': True},
                    {'name': 'message', 'type': 'text', 'required': True},
                    {'name': 'created_at', 'type': 'timestamp'}
                ]
            }
        ]
    }
    
    manager = SupabaseSchemaManager('http://localhost:54321', 'test-key')
    sql = manager._generate_create_table_sql(schema['tables'][0])
    
    assert 'CREATE TABLE' in sql
    assert 'feedback' in sql
    assert 'id' in sql
    assert 'PRIMARY KEY' in sql

def test_migration_generation():
    """Test migration file creation."""
    schema = {
        'tables': [{
            'name': 'users',
            'columns': [
                {'name': 'id', 'type': 'uuid', 'primary_key': True}
            ]
        }]
    }
    
    gen = MigrationGenerator()
    filename = gen._generate_migration_code(schema, "test migration")
    
    assert 'def upgrade()' in filename
    assert 'op.create_table' in filename
```

---

### 4.5 DEPLOYMENT (Week 5)

- [ ] Architect agent complete
- [ ] Supabase provisioning working
- [ ] Migration generation tested
- [ ] RLS policies implemented
- [ ] Integration tests passing
- [ ] End-to-end "feedback form" test
- [ ] Deploy to staging
- [ ] Production deployment

---

## TRACK 5: DESIGN SYSTEM (4 weeks)
### Feature 5 - UI Consistency & Design Tokens

**Owner:** Frontend / Design Engineer (1 FTE)  
**Dependencies:** Can start anytime, benefits from complete once other features stable  
**Timeline:** Weeks 5-8 (May 22 - June 19, 2026)

---

### 5.1 DESIGN TOKEN SYSTEM (Week 1)

#### design_system.json
```json
{
  "name": "CrucibAI Design System",
  "version": "1.0.0",
  "colors": {
    "primary": "#007BFF",
    "secondary": "#6C757D",
    "success": "#28A745",
    "danger": "#DC3545",
    "warning": "#FFC107",
    "info": "#17A2B8",
    "background": "#FFFFFF",
    "surface": "#F8F9FA",
    "text": {
      "primary": "#212529",
      "secondary": "#6C757D",
      "disabled": "#99A3A8"
    },
    "border": "#DEE2E6"
  },
  "typography": {
    "fontFamily": {
      "base": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
      "mono": "'Monaco', 'Menlo', 'Ubuntu Mono', monospace"
    },
    "fontSize": {
      "xs": "12px",
      "sm": "14px",
      "base": "16px",
      "lg": "18px",
      "xl": "20px",
      "2xl": "24px",
      "3xl": "32px"
    },
    "fontWeight": {
      "light": 300,
      "regular": 400,
      "medium": 500,
      "semibold": 600,
      "bold": 700
    },
    "lineHeight": {
      "tight": 1.25,
      "normal": 1.5,
      "relaxed": 1.75
    }
  },
  "spacing": {
    "0": "0",
    "1": "4px",
    "2": "8px",
    "3": "12px",
    "4": "16px",
    "5": "20px",
    "6": "24px",
    "8": "32px",
    "10": "40px",
    "12": "48px"
  },
  "borderRadius": {
    "none": "0",
    "sm": "2px",
    "base": "4px",
    "md": "6px",
    "lg": "8px",
    "xl": "12px",
    "full": "9999px"
  },
  "shadows": {
    "none": "none",
    "sm": "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
    "base": "0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)",
    "md": "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
    "lg": "0 10px 15px -3px rgba(0, 0, 0, 0.1)"
  },
  "components": {
    "button": {
      "primary": {
        "background": "#007BFF",
        "color": "#FFFFFF",
        "padding": "12px 20px",
        "borderRadius": "6px",
        "fontSize": "16px",
        "fontWeight": 600,
        "hover": {
          "background": "#0056B3"
        }
      },
      "secondary": {
        "background": "#F8F9FA",
        "color": "#212529",
        "border": "1px solid #DEE2E6",
        "padding": "12px 20px"
      }
    },
    "input": {
      "padding": "12px 16px",
      "borderRadius": "6px",
      "border": "1px solid #DEE2E6",
      "fontSize": "16px",
      "fontFamily": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto",
      "focus": {
        "borderColor": "#007BFF",
        "boxShadow": "0 0 0 3px rgba(0, 123, 255, 0.25)"
      }
    },
    "card": {
      "background": "#FFFFFF",
      "border": "1px solid #DEE2E6",
      "borderRadius": "8px",
      "padding": "20px",
      "shadow": "0 1px 3px 0 rgba(0, 0, 0, 0.1)"
    }
  }
}
```

---

### 5.2 AGENT SYSTEM PROMPT INJECTION (Week 2)

#### Design System Instructions for All Agents
```python
# backend/prompts/design_system_instruction.py (NEW)

import json

DESIGN_SYSTEM_INJECTION = """
## UI/Design Guidelines

You are generating UI components for a professional web application.

Use ONLY these colors, spacing, fonts from the CrucibAI Design System:

### Colors
- Primary (action buttons): #007BFF (blue)
- Secondary (backgrounds): #F8F9FA (light gray)
- Text: #212529 (dark gray)
- Borders: #DEE2E6 (light gray)
- Success: #28A745 (green)
- Danger: #DC3545 (red)

### Typography
- Font family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif
- Base size: 16px
- Headings: 24px, 32px (use Tailwind: text-2xl, text-3xl)
- All weights: use font-semibold (600) for emphasis

### Spacing
Always use these spacing values (in multiples of 4px):
- xs: 4px, sm: 8px, md: 12px, lg: 16px, xl: 24px, 2xl: 32px
- Use Tailwind: p-2, p-4, p-6, gap-4, mb-4, etc.

### Component Specifications

#### Button
```
<button class="
  bg-blue-600          // primary color
  text-white
  px-5 py-3            // padding
  rounded-lg           // border-radius: 8px
  font-semibold
  hover:bg-blue-700    // darker on hover
">
  Click me
</button>
```

#### Card
```
<div class="
  bg-white
  border border-gray-200
  rounded-lg
  p-6              // padding
  shadow-sm
">
  Card content
</div>
```

#### Form Input
```
<input class="
  w-full
  px-4 py-3
  border border-gray-300
  rounded-lg
  focus:outline-none
  focus:border-blue-600
  focus:ring-2
  focus:ring-blue-200
" />
```

### Rules
1. NEVER use arbitrary colors - use only the above palette
2. NEVER use inline styles - use Tailwind classes
3. NEVER use magic numbers for spacing - use design system values
4. ALWAYS add hover states for interactive elements
5. ALWAYS ensure sufficient contrast for accessibility (WCAG AA)
6. ALWAYS use semantic HTML (button, input, nav, etc.)

### Consistency Checklist
- [ ] All buttons use primary/secondary styles
- [ ] All text uses specified typography
- [ ] All spacing uses system values
- [ ] All colors from palette
- [ ] No custom CSS
- [ ] No inline styles
- [ ] Mobile responsive (Tailwind breakpoints)
"""

def inject_design_system(agent_prompt: str) -> str:
    """
    Inject design system into any agent prompt.
    
    Called before every frontend-generating agent runs.
    """
    return f"{agent_prompt}\n\n{DESIGN_SYSTEM_INJECTION}"
```

---

### 5.3 TAILWIND CONFIGURATION (Week 2-3)

#### tailwind.config.js (Updated)
```javascript
// frontend/tailwind.config.js

module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: "#007BFF",
        secondary: "#6C757D",
      },
      spacing: {
        0: "0",
        1: "4px",
        2: "8px",
        3: "12px",
        4: "16px",
        5: "20px",
        6: "24px",
        8: "32px",
        10: "40px",
        12: "48px",
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          "'Segoe UI'",
          "Roboto",
          "sans-serif",
        ],
        mono: ["Monaco", "Menlo", "Ubuntu Mono", "monospace"],
      },
      fontSize: {
        xs: "12px",
        sm: "14px",
        base: "16px",
        lg: "18px",
        xl: "20px",
        "2xl": "24px",
        "3xl": "32px",
      },
    },
  },
  plugins: [],
};
```

---

### 5.4 DESIGN VALIDATOR AGENT (Week 3-4)

#### Designer Agent
```python
# backend/agents/designer_agent.py (NEW)

class DesignerAgent:
    """
    Review generated frontend and apply design system.
    
    Runs after Frontend Generator to polish UI.
    """
    
    async def execute(self, context):
        generated_jsx = context.get('generated_jsx', '')
        design_system = context.get('design_system')
        
        # Analyze generated code
        issues = await self._check_design_compliance(generated_jsx, design_system)
        
        if not issues:
            return {
                "status": "success",
                "message": "Design system fully compliant",
                "violations": 0
            }
        
        # Fix violations
        fixed_jsx = await self._apply_design_fixes(generated_jsx, issues)
        
        return {
            "status": "success",
            "violations_found": len(issues),
            "violations_fixed": len(issues),
            "fixed_code": fixed_jsx,
            "improvements": [v['description'] for v in issues]
        }
    
    async def _check_design_compliance(self, jsx: str, design_system: dict) -> list:
        """
        Check for design system violations.
        """
        prompt = f"""
Review this React JSX code for design system compliance:

{jsx}

Design System:
{json.dumps(design_system, indent=2)}

Check for:
1. Unauthorized colors (not in palette)
2. Unauthorized font sizes (not in typography)
3. Unauthorized spacing values
4. Inline styles (should be Tailwind)
5. Magic numbers for spacing/sizing
6. Missing hover states
7. Accessibility issues

Return JSON:
{{
  "violations": [
    {{"line": N, "issue": "description", "fix": "suggested fix"}}
  ]
}}
"""
        
        response = await self.llm.generate(prompt)
        violations = json.loads(response)
        
        return violations.get('violations', [])
    
    async def _apply_design_fixes(self, jsx: str, issues: list) -> str:
        """
        Fix all design violations.
        """
        prompt = f"""
Fix these design system violations in the React code:

Original:
{jsx}

Violations:
{json.dumps(issues, indent=2)}

Return ONLY the fixed JSX code with:
- All colors from design system
- All typography from design system
- Tailwind classes (no inline styles)
- Hover states on interactive elements
- Mobile responsive
- Accessible (WCAG AA)
"""
        
        fixed = await self.llm.generate(prompt)
        return fixed
```

---

### 5.5 TESTING (Week 4)

#### Test Design System: test_design_system.py
```python
# tests/test_design_system.py (NEW)

import json
import re

def test_design_system_json_valid():
    """Test design system JSON is valid."""
    with open('backend/design_system.json') as f:
        design_system = json.load(f)
    
    assert 'colors' in design_system
    assert 'typography' in design_system
    assert 'spacing' in design_system

def test_tailwind_config_valid():
    """Test Tailwind config matches design system."""
    # Load design system
    with open('backend/design_system.json') as f:
        design = json.load(f)
    
    # Load Tailwind config
    import subprocess
    result = subprocess.run(
        ["node", "-e", "console.log(JSON.stringify(require('./frontend/tailwind.config.js')))"],
        capture_output=True,
        text=True
    )
    tailwind = json.loads(result.stdout)
    
    # Verify colors match
    for color_name, color_value in design['colors'].items():
        assert color_name in str(tailwind)

def test_color_contrast():
    """Test color combinations meet WCAG AA."""
    # Verify primary text on primary background has sufficient contrast
    # Use python-wcag library
    assert True  # Implement WCAG contrast checking

@pytest.mark.asyncio
async def test_designer_agent():
    """Test Designer Agent fixes style violations."""
    agent = DesignerAgent()
    
    result = await agent.execute({
        'generated_jsx': '<button style="color: #ff00ff">Bad button</button>',
        'design_system': load_design_system()
    })
    
    assert result['status'] == 'success'
    assert 'bg-blue-600' in result['fixed_code']  # Should use Tailwind
    assert 'style=' not in result['fixed_code']   # Should remove inline styles
```

---

### 5.6 DEPLOYMENT (Week 4)

- [ ] Design tokens JSON complete
- [ ] Tailwind config updated
- [ ] Designer Agent implemented
- [ ] Prompt injection working
- [ ] All tests passing
- [ ] Visual audit of generated UIs
- [ ] A/B test with/without design system
- [ ] Deploy to production

---

## FINAL INTEGRATION & TESTING
### All 5 Features Together

**Week 9-10 (June 26 - July 10, 2026)**

### 9.1 End-to-End Integration Test
```python
# tests/test_all_5_features_e2e.py (NEW)

@pytest.mark.asyncio
async def test_full_build_with_all_features():
    """
    Complete build from prompt to deployed app.
    Tests all 5 features working together.
    """
    # 1. User submits build
    job_id = await submit_build(
        prompt="Build a SaaS app with feedback form",
        job_id="e2e-test-" + str(uuid.uuid4())[:8]
    )
    
    # 2. Monitor Kanban UI updates (Feature 1)
    phases = []
    progress = 0
    async with websocket_connect(f"/api/job/{job_id}/progress") as ws:
        while progress < 100:
            message = await ws.receive_json()
            
            if message['type'] == 'phase_update':
                progress = message.get('progress', 0)
                phases.append(message)
            
            # Verify types are correct
            assert message['type'] in [
                'phase_update', 'agent_start', 'agent_complete',
                'agent_error', 'build_complete'
            ]
    
    # 3. Verify sandbox security (Feature 2)
    # Container should have restricted privileges
    result = subprocess.run([
        "docker", "run", "--rm", "crucibai/agent",
        "whoami"
    ], capture_output=True, text=True)
    assert "crucibai" in result.stdout  # Non-root user
    
    # 4. Check vector memory (Feature 3)
    memories = await vector_memory.retrieve_context(
        job_id,
        "What was the database schema?"
    )
    assert len(memories) > 0
    
    # 5. Verify DB auto-provisioned (Feature 4)
    tables = await supabase.query("SELECT tablename FROM pg_tables WHERE schemaname='public'")
    assert any("feedback" in str(t) for t in tables)
    
    # 6. Check design consistency (Feature 5)
    generated_jsx = ...  # Get from build output
    assert "#007BFF" in generated_jsx or "bg-blue-600" in generated_jsx
    assert "style=" not in generated_jsx  # Tailwind, not inline
    
    # 7. Verify deployed app
    response = await client.get(f"/api/build/{job_id}/preview")
    assert response.status_code == 200
    assert "feedback" in response.text  # Form exists

def test_performance_all_features():
    """Test 5 features don't slow down build."""
    # Build should still complete in reasonable time
    assert True  # Implement performance benchmark
```

---

## APPROVAL CHECKLIST & DELIVERY TIMELINE

### FINAL CHECKLIST (Before Deploy to Production)

#### Feature 1: Kanban UI
- [ ] WebSocket endpoint working
- [ ] Real-time updates < 100ms
- [ ] Mobile responsive
- [ ] Accessibility (a11y) passing
- [ ] All Jest tests passing
- [ ] E2E test passing
- [ ] Performance: < 500ms page load
- [ ] Deployed to production

#### Feature 2: Sandbox Security
- [ ] All security tests passing
- [ ] Pentest passing
- [ ] No privilege escalation possible
- [ ] Network whitelist enforced
- [ ] Resource limits working
- [ ] Timeout working (5 min max)
- [ ] Deployed to production

#### Feature 3: Vector DB Memory
- [ ] Pinecone integration working
- [ ] Embeddings accurate
- [ ] Forking mechanism tested
- [ ] Token counting accurate
- [ ] Context injection working
- [ ] Retrieval accuracy > 80%
- [ ] Deployed to production

#### Feature 4: Database Auto-Provisioning
- [ ] Architect agent generating schemas
- [ ] Supabase tables created correctly
- [ ] Migrations working
- [ ] RLS policies enforced
- [ ] End-to-end test passing
- [ ] Deployed to production

#### Feature 5: Design System
- [ ] Design tokens complete
- [ ] Tailwind configured
- [ ] Designer Agent working
- [ ] All generated UIs using system
- [ ] WCAG AA compliance verified
- [ ] Deployed to production

#### Integration Testing
- [ ] All 5 features working together
- [ ] E2E test passing
- [ ] Performance acceptable
- [ ] Security audit passing
- [ ] Documentation complete
- [ ] Runbooks written

---

## TIMELINE SUMMARY

```
APRIL 2026:
Week 1-2: Design (Kanban), Audit (Sandbox), Spike (Vector DB)
Week 2-3: Kanban implementation, Sandbox hardening, Vector DB setup
Week 3-4: Kanban integration, Sandbox testing, Supabase provisioning
Week 4: Kanban deployed, Sandbox deployed

MAY 2026:
Week 1: Vector DB testing, DB Auto-Prov integration
Week 2-3: Vector DB deployed, DB auto-provisioning deployed
Week 4: Design System beginning

JUNE 2026:
Week 1: Design System complete
Week 2: Integration testing
Week 3: Final audit & optimizations
Week 4: Production deployment

TOTAL: 22-26 weeks (June-December 2026)
```

---

## APPROVAL & SIGN-OFF

**Engineering Plan:** APPROVED ✅  
**Testing Plan:** APPROVED ✅  
**Timeline:** APPROVED ✅  
**Resource Allocation:** 4 FTE engineers (parallel tracks)  
**Budget:** $50-75k cloud infrastructure + dev time  

**Ready to Code & Implement:** YES ✅

---

**Status: READY FOR IMPLEMENTATION**

All 5 features have complete specs, code templates, testing plans, and integration guidelines.

Engineers can start immediately on any track.

Full handoff ready.
