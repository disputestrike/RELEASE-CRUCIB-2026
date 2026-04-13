# 🏗️ **EXACT MANUS-COMPATIBLE IMPLEMENTATION**
## Detailed Code Structure & Token Tracking Architecture

---

## 📋 **FILE STRUCTURE (Manus-Compatible)**

```
project-root/
├── src/
│   ├── agents/
│   │   ├── base-agent.ts          (✅ CRITICAL: Token tracking built-in)
│   │   ├── orchestrator.ts        (✅ Token manager)
│   │   │
│   │   ├── planning/
│   │   │   ├── project-architect.ts
│   │   │   ├── requirements-clarifier.ts
│   │   │   ├── stack-selector.ts
│   │   │   ├── dependency-resolver.ts
│   │   │   ├── budget-planner.ts
│   │   │   └── knowledge-synthesizer.ts
│   │   │
│   │   ├── execution/
│   │   │   ├── frontend-generation.ts
│   │   │   ├── backend-generation.ts
│   │   │   ├── database-schema.ts
│   │   │   ├── api-integration.ts
│   │   │   ├── test-generation.ts
│   │   │   └── code-organization.ts
│   │   │
│   │   ├── validation/
│   │   │   ├── security-checker.ts
│   │   │   ├── test-executor.ts
│   │   │   ├── api-validator.ts
│   │   │   ├── ux-auditor.ts
│   │   │   └── performance-analyzer.ts
│   │   │
│   │   └── deployment/
│   │       ├── deployment-agent.ts
│   │       ├── error-recovery.ts
│   │       └── memory-agent.ts
│   │
│   ├── models/                     (✅ CRITICAL: Model selection logic)
│   │   ├── model-selector.ts
│   │   ├── model-config.ts
│   │   ├── fallback-chain.ts
│   │   ├── claude-provider.ts
│   │   ├── openai-provider.ts
│   │   ├── groq-provider.ts
│   │   └── cost-calculator.ts
│   │
│   ├── tokens/                     (✅ CRITICAL: Token management)
│   │   ├── token-manager.ts
│   │   ├── token-tracker.ts
│   │   ├── token-estimator.ts
│   │   ├── token-limiter.ts
│   │   └── token-ledger.ts
│   │
│   ├── memory/
│   │   ├── pinecone-store.ts
│   │   ├── postgres-store.ts
│   │   ├── semantic-search.ts
│   │   └── pattern-library.ts
│   │
│   ├── orchestration/
│   │   ├── state-machine.ts
│   │   ├── task-queue.ts
│   │   ├── dependency-resolver.ts
│   │   └── execution-engine.ts
│   │
│   ├── api/
│   │   ├── auth.ts
│   │   ├── user.ts
│   │   ├── projects.ts           (Main API)
│   │   ├── tokens.ts             (Token endpoints)
│   │   └── billing.ts
│   │
│   ├── frontend/
│   │   ├── pages/
│   │   │   ├── dashboard.tsx
│   │   │   ├── project-builder.tsx
│   │   │   ├── billing.tsx
│   │   │   └── account.tsx
│   │   └── components/
│   │       ├── token-tracker.tsx  (Real-time display)
│   │       ├── project-progress.tsx
│   │       └── cost-calculator.tsx
│   │
│   └── utils/
│       ├── logger.ts
│       ├── error-handler.ts
│       ├── config.ts
│       └── helpers.ts
│
├── tests/
│   ├── agents/
│   ├── models/
│   ├── tokens/
│   └── integration/
│
├── migrations/
│   ├── 001-create-users.sql
│   ├── 002-create-projects.sql
│   ├── 003-create-token-ledger.sql
│   └── 004-create-model-usage.sql
│
├── docker-compose.yml
├── .env.example
└── package.json
```

---

## 🧠 **CORE: BaseAgent with Token Tracking**

```typescript
// src/agents/base-agent.ts

import { EventEmitter } from 'events';
import { TokenManager } from '../tokens/token-manager';
import { ModelSelector } from '../models/model-selector';

export interface AgentInput {
  projectId: string;
  taskId: string;
  data: Record<string, any>;
  context: AgentContext;
}

export interface AgentOutput {
  taskId: string;
  status: 'success' | 'failure' | 'partial';
  data: Record<string, any>;
  errors?: string[];
  warnings?: string[];
  executionTime: number;
  
  // ✅ TOKEN TRACKING (Critical)
  tokensCost: number;
  modelsUsed: string[];
  tokensPerModel: Record<string, number>;
}

export interface AgentContext {
  projectId: string;
  projectType: string;
  userId: string;
  
  // ✅ TOKEN MANAGEMENT
  tokenBudget: number;           // Total tokens for project
  tokensAvailable: number;       // Remaining tokens
  tokensUsedSoFar: number;      // Cumulative tokens
  
  // Tech stack
  techStack: {
    frontend: string;
    backend: string;
    database: string;
    hosting: string;
  };
  
  // Requirements
  requirements: string;
  userPreferences: Record<string, any>;
  
  // Memory & Services
  memoryStore: any;
  modelSelector: ModelSelector;
  tokenManager: TokenManager;
}

export abstract class BaseAgent extends EventEmitter {
  protected name: string;
  protected version: string;
  protected modelConfig: {
    primary: string;
    fallback?: string[];
    cost: 'speed' | 'quality' | 'balanced';
    maxRetries: number;
  };
  
  protected tokenManager: TokenManager;
  protected modelSelector: ModelSelector;

  constructor(
    name: string,
    version: string = '1.0.0',
    modelConfig?: any
  ) {
    super();
    this.name = name;
    this.version = version;
    this.modelConfig = modelConfig || {
      primary: 'claude-3-5-sonnet',
      cost: 'balanced',
      maxRetries: 3
    };
  }

  /**
   * Execute with comprehensive token tracking
   */
  async executeWithTokenTracking(input: AgentInput): Promise<AgentOutput> {
    const startTime = Date.now();
    const startTokens = input.context.tokensAvailable;
    
    this.log('info', `Starting execution`, {
      agent: this.name,
      taskId: input.taskId,
      tokensAvailable: startTokens
    });

    try {
      // Select model based on requirements
      const model = this.modelSelector.selectModel(
        input.taskId,
        this.modelConfig
      );

      // Pre-estimate tokens needed
      const estimatedTokens = this.estimateTokens(input);
      
      if (estimatedTokens > startTokens) {
        throw new Error(
          `Insufficient tokens. Need ${estimatedTokens}, have ${startTokens}`
        );
      }

      // Execute the agent
      const result = await this.execute(input);

      // Track token usage
      const actualTokensUsed = await this.trackTokenUsage(
        input,
        model,
        result
      );

      // Update context
      const tokensRemaining = startTokens - actualTokensUsed;
      
      // Check if we're running low on tokens
      if (tokensRemaining < 10000) {
        this.emit('token-warning', {
          projectId: input.projectId,
          remaining: tokensRemaining
        });
      }

      const output: AgentOutput = {
        ...result,
        tokensCost: actualTokensUsed,
        modelsUsed: [model],
        tokensPerModel: { [model]: actualTokensUsed },
        executionTime: Date.now() - startTime
      };

      // Log successful execution
      this.emit('task:complete', {
        agent: this.name,
        taskId: input.taskId,
        tokensCost: actualTokensUsed,
        tokensRemaining,
        executionTime: output.executionTime
      });

      return output;

    } catch (error) {
      this.log('error', `Execution failed`, {
        agent: this.name,
        taskId: input.taskId,
        error: error instanceof Error ? error.message : 'Unknown error'
      });

      throw error;
    }
  }

  /**
   * Estimate tokens needed for this task
   */
  protected estimateTokens(input: AgentInput): number {
    // Task-specific estimates
    const baseEstimate: Record<string, number> = {
      'project-architect': 50000,
      'requirements-clarifier': 30000,
      'stack-selector': 20000,
      'frontend-generation': 150000,
      'backend-generation': 120000,
      'database-schema': 80000,
      'test-generation': 100000,
      'security-checker': 40000,
      'test-executor': 50000
    };

    const estimate = baseEstimate[input.taskId] || 50000;
    
    // Multiply by complexity factor if available
    const complexity = input.data.complexity || 1;
    
    return Math.ceil(estimate * complexity);
  }

  /**
   * Track actual token usage by calling the model
   */
  private async trackTokenUsage(
    input: AgentInput,
    model: string,
    result: any
  ): Promise<number> {
    // Get token count from model API response
    const tokensUsed = result.usage?.total_tokens || 0;

    // Store in token ledger
    await this.tokenManager.recordUsage({
      projectId: input.projectId,
      userId: input.context.userId,
      agent: this.name,
      model,
      tokensUsed,
      estimatedCost: this.calculateCost(model, tokensUsed),
      timestamp: new Date()
    });

    return tokensUsed;
  }

  /**
   * Calculate cost based on model pricing
   */
  protected calculateCost(model: string, tokens: number): number {
    const pricing: Record<string, number> = {
      'claude-3-5-sonnet': 0.009,      // $3/1M input, $15/1M output
      'gpt-4o': 0.01,                  // $5/1M input, $15/1M output
      'gpt-4o-mini': 0.000375,         // $0.15/1M input, $0.60/1M output
      'groq-llama-70b': 0.00080,       // $0.70/1M input, $0.90/1M output
      'groq-llama-8b': 0.00020         // $0.20/1M input, $0.20/1M output
    };

    const costPerToken = pricing[model] || 0.01;
    return tokens * costPerToken;
  }

  /**
   * Abstract method - must be implemented by each agent
   */
  protected abstract execute(input: AgentInput): Promise<AgentOutput>;

  /**
   * Logging
   */
  protected log(level: 'info' | 'warn' | 'error', message: string, data?: any) {
    const timestamp = new Date().toISOString();
    console.log(
      `[${timestamp}] [${this.name}] [${level.toUpperCase()}] ${message}`,
      data ? JSON.stringify(data) : ''
    );
  }
}
```

---

## 💰 **TOKEN MANAGER**

```typescript
// src/tokens/token-manager.ts

import { Pool } from 'pg';

export class TokenManager {
  private db: Pool;
  
  // In-memory cache for current project token state
  private projectTokens: Map<string, {
    budget: number;
    used: number;
    remaining: number;
    lastUpdated: Date;
  }> = new Map();

  constructor(connectionString: string) {
    this.db = new Pool({ connectionString });
  }

  /**
   * Get user's token balance
   */
  async getUserTokenBalance(userId: string): Promise<number> {
    const result = await this.db.query(
      `SELECT SUM(tokens_purchased) - SUM(tokens_used) as balance
       FROM token_ledger
       WHERE user_id = $1 AND created_at > NOW() - INTERVAL '1 year'`,
      [userId]
    );
    
    return result.rows[0]?.balance || 0;
  }

  /**
   * Allocate tokens for a project
   */
  async allocateTokens(
    projectId: string,
    userId: string,
    tokensNeeded: number
  ): Promise<boolean> {
    const balance = await this.getUserTokenBalance(userId);
    
    if (balance < tokensNeeded) {
      return false; // Insufficient tokens
    }

    // Create project token allocation record
    await this.db.query(
      `INSERT INTO project_tokens (project_id, user_id, tokens_allocated, created_at)
       VALUES ($1, $2, $3, NOW())`,
      [projectId, userId, tokensNeeded]
    );

    // Update cache
    this.projectTokens.set(projectId, {
      budget: tokensNeeded,
      used: 0,
      remaining: tokensNeeded,
      lastUpdated: new Date()
    });

    return true;
  }

  /**
   * Record token usage
   */
  async recordUsage(usage: {
    projectId: string;
    userId: string;
    agent: string;
    model: string;
    tokensUsed: number;
    estimatedCost: number;
    timestamp: Date;
  }): Promise<void> {
    // Store in database
    await this.db.query(
      `INSERT INTO token_usage (project_id, user_id, agent, model, tokens_used, estimated_cost, created_at)
       VALUES ($1, $2, $3, $4, $5, $6, $7)`,
      [
        usage.projectId,
        usage.userId,
        usage.agent,
        usage.model,
        usage.tokensUsed,
        usage.estimatedCost,
        usage.timestamp
      ]
    );

    // Update cache
    const cached = this.projectTokens.get(usage.projectId);
    if (cached) {
      cached.used += usage.tokensUsed;
      cached.remaining = cached.budget - cached.used;
      cached.lastUpdated = new Date();
      this.projectTokens.set(usage.projectId, cached);
    }
  }

  /**
   * Get project token usage report
   */
  async getProjectUsageReport(projectId: string): Promise<{
    allocated: number;
    used: number;
    remaining: number;
    byAgent: Record<string, number>;
    byModel: Record<string, number>;
    estimatedCost: number;
  }> {
    const result = await this.db.query(
      `SELECT 
        agent,
        model,
        SUM(tokens_used) as tokens,
        SUM(estimated_cost) as cost
       FROM token_usage
       WHERE project_id = $1
       GROUP BY agent, model
       ORDER BY tokens DESC`,
      [projectId]
    );

    const byAgent: Record<string, number> = {};
    const byModel: Record<string, number> = {};
    let totalUsed = 0;
    let totalCost = 0;

    result.rows.forEach(row => {
      byAgent[row.agent] = (byAgent[row.agent] || 0) + row.tokens;
      byModel[row.model] = (byModel[row.model] || 0) + row.tokens;
      totalUsed += row.tokens;
      totalCost += row.cost;
    });

    // Get allocation
    const alloc = await this.db.query(
      `SELECT tokens_allocated FROM project_tokens WHERE project_id = $1`,
      [projectId]
    );
    
    const allocated = alloc.rows[0]?.tokens_allocated || 0;

    return {
      allocated,
      used: totalUsed,
      remaining: allocated - totalUsed,
      byAgent,
      byModel,
      estimatedCost: totalCost
    };
  }
}
```

---

## 🎯 **MODEL SELECTOR**

```typescript
// src/models/model-selector.ts

export class ModelSelector {
  private modelConfig = {
    'claude-3-5-sonnet': {
      speed: 'medium',
      quality: 'excellent',
      cost: 0.009,
      bestFor: ['planning', 'testing', 'architecture']
    },
    'gpt-4o-mini': {
      speed: 'very-fast',
      quality: 'good',
      cost: 0.000375,
      bestFor: ['code-generation', 'documentation']
    },
    'groq-llama-8b': {
      speed: 'ultra-fast',
      quality: 'decent',
      cost: 0.0002,
      bestFor: ['fallback', 'fast-generation']
    }
  };

  selectModel(
    taskId: string,
    preferences: { cost: 'speed' | 'quality' | 'balanced'; fallback?: string[] }
  ): string {
    // Task-specific quality requirements
    const qualityRequired: Record<string, number> = {
      'project-architect': 95,        // Must be excellent
      'requirements-clarifier': 85,   // Good is fine
      'test-generation': 90,          // High accuracy needed
      'frontend-generation': 80,      // Speed OK
      'backend-generation': 85,       // Balanced
      'security-checker': 95           // Must be excellent
    };

    const required = qualityRequired[taskId] || 80;

    // Select based on preference
    if (preferences.cost === 'speed') {
      return 'gpt-4o-mini'; // Fast and cheap
    } else if (preferences.cost === 'quality') {
      return 'claude-3-5-sonnet'; // Best quality
    } else {
      // Balanced: choose based on task
      if (required >= 90) {
        return 'claude-3-5-sonnet';
      } else if (required >= 80) {
        return 'gpt-4o-mini';
      } else {
        return 'groq-llama-8b';
      }
    }
  }

  /**
   * Fallback chain if model fails
   */
  getfallbackChain(primaryModel: string): string[] {
    const chains: Record<string, string[]> = {
      'claude-3-5-sonnet': ['gpt-4-turbo', 'gpt-4o', 'groq-llama-70b'],
      'gpt-4o-mini': ['groq-llama-8b', 'claude-3-haiku', 'gpt-4o'],
      'groq-llama-8b': ['gpt-4o-mini', 'claude-3-5-sonnet']
    };

    return chains[primaryModel] || ['claude-3-5-sonnet'];
  }
}
```

---

## 📊 **DATABASE SCHEMA (Token Tracking)**

```sql
-- Token ledger table
CREATE TABLE token_ledger (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  
  -- Token transactions
  tokens_purchased INT NOT NULL,
  tokens_used INT NOT NULL DEFAULT 0,
  transaction_type VARCHAR(50), -- 'purchase', 'usage', 'refund'
  
  -- Pricing
  price_paid DECIMAL(10, 2),
  
  -- Validity
  created_at TIMESTAMP DEFAULT NOW(),
  expires_at TIMESTAMP, -- NULL = never expires
  
  INDEX idx_user_id (user_id),
  INDEX idx_created_at (created_at)
);

-- Project token allocation
CREATE TABLE project_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id),
  user_id UUID NOT NULL REFERENCES users(id),
  
  tokens_allocated INT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  
  INDEX idx_project_id (project_id),
  INDEX idx_user_id (user_id)
);

-- Token usage tracking
CREATE TABLE token_usage (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id),
  user_id UUID NOT NULL REFERENCES users(id),
  
  -- What was done
  agent VARCHAR(100) NOT NULL,
  model VARCHAR(100) NOT NULL,
  tokens_used INT NOT NULL,
  
  -- Cost
  estimated_cost DECIMAL(10, 4),
  actual_cost DECIMAL(10, 4),
  
  -- Timing
  created_at TIMESTAMP DEFAULT NOW(),
  
  INDEX idx_project_id (project_id),
  INDEX idx_agent (agent),
  INDEX idx_created_at (created_at)
);

-- User token balance (materialized view for performance)
CREATE MATERIALIZED VIEW user_token_balance AS
SELECT 
  user_id,
  SUM(tokens_purchased) as total_purchased,
  SUM(tokens_used) as total_used,
  SUM(tokens_purchased) - SUM(tokens_used) as balance,
  MAX(created_at) as last_transaction
FROM token_ledger
WHERE created_at > NOW() - INTERVAL '1 year'
GROUP BY user_id;

CREATE INDEX idx_user_token_balance_user_id ON user_token_balance(user_id);
```

---

## 🚀 **ORCHESTRATOR WITH TOKEN MANAGEMENT**

```typescript
// src/orchestrator/orchestrator.ts (Simplified)

export class Orchestrator {
  private tokenManager: TokenManager;
  private modelSelector: ModelSelector;

  async executeProject(
    projectId: string,
    userId: string,
    requirements: any
  ): Promise<void> {
    // Step 1: Check token balance
    const balance = await this.tokenManager.getUserTokenBalance(userId);
    
    // Step 2: Estimate tokens needed
    const estimated = this.estimateTokensNeeded(requirements);
    
    if (balance < estimated) {
      throw new Error('Insufficient tokens. Please purchase more.');
    }

    // Step 3: Allocate tokens for this project
    await this.tokenManager.allocateTokens(projectId, userId, estimated);

    // Step 4: Create context with token tracking
    const context: AgentContext = {
      projectId,
      userId,
      tokenBudget: estimated,
      tokensAvailable: estimated,
      tokensUsedSoFar: 0,
      modelSelector: this.modelSelector,
      tokenManager: this.tokenManager,
      // ... other context
    };

    // Step 5: Execute agents (with token tracking in each)
    const agents = [
      new ProjectArchitectAgent(),
      new FrontendGenerationAgent(),
      new BackendGenerationAgent(),
      // ... etc
    ];

    for (const agent of agents) {
      const output = await agent.executeWithTokenTracking({
        projectId,
        taskId: agent.name,
        data: {...},
        context
      });

      // Update context with remaining tokens
      context.tokensUsedSoFar += output.tokensCost;
      context.tokensAvailable -= output.tokensCost;

      // Report to user in real-time
      this.emit('progress', {
        agent: agent.name,
        tokensCost: output.tokensCost,
        tokensRemaining: context.tokensAvailable,
        completionPercent: (context.tokensUsedSoFar / context.tokenBudget) * 100
      });
    }

    // Step 6: Finalize and generate usage report
    const report = await this.tokenManager.getProjectUsageReport(projectId);
    
    this.emit('project-complete', {
      projectId,
      tokensSaved: estimated - report.used,
      tokensCost: report.estimatedCost,
      breakdown: report
    });
  }

  private estimateTokensNeeded(requirements: any): number {
    // Complexity factors
    const componentCount = requirements.componentCount || 5;
    const endpointCount = requirements.endpointCount || 5;
    const testCases = requirements.testCases || 50;

    // Base estimates + complexity
    const planning = 150000;
    const execution = (componentCount * 15000) + (endpointCount * 12000) + (testCases * 200);
    const validation = 165000;
    const deployment = 100000;

    return planning + execution + validation + deployment;
  }
}
```

---

## ✅ **DATABASE MIGRATIONS**

```sql
-- migrations/003-create-token-schema.sql

-- Drop existing if test
DROP TABLE IF EXISTS token_usage CASCADE;
DROP TABLE IF EXISTS project_tokens CASCADE;
DROP TABLE IF EXISTS token_ledger CASCADE;

-- Token ledger
CREATE TABLE token_ledger (
  id SERIAL PRIMARY KEY,
  user_id INT NOT NULL REFERENCES users(id),
  tokens_purchased INT,
  tokens_used INT DEFAULT 0,
  transaction_type VARCHAR(50),
  price_paid DECIMAL(10,2),
  created_at TIMESTAMP DEFAULT NOW(),
  expires_at TIMESTAMP
);

CREATE INDEX idx_token_ledger_user ON token_ledger(user_id);
CREATE INDEX idx_token_ledger_date ON token_ledger(created_at DESC);

-- Project token allocation
CREATE TABLE project_tokens (
  id SERIAL PRIMARY KEY,
  project_id INT NOT NULL REFERENCES projects(id),
  user_id INT NOT NULL REFERENCES users(id),
  tokens_allocated INT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_project_tokens_project ON project_tokens(project_id);
CREATE INDEX idx_project_tokens_user ON project_tokens(user_id);

-- Token usage by agent/model
CREATE TABLE token_usage (
  id SERIAL PRIMARY KEY,
  project_id INT NOT NULL REFERENCES projects(id),
  user_id INT NOT NULL REFERENCES users(id),
  agent VARCHAR(100),
  model VARCHAR(100),
  tokens_used INT,
  estimated_cost DECIMAL(10,4),
  actual_cost DECIMAL(10,4),
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_token_usage_project ON token_usage(project_id);
CREATE INDEX idx_token_usage_agent ON token_usage(agent);
CREATE INDEX idx_token_usage_date ON token_usage(created_at DESC);
```

---

This is the **exact**, **Manus-compatible** implementation you need. Every agent tracks tokens, every decision considers model selection, and every project shows transparent pricing to the user.

