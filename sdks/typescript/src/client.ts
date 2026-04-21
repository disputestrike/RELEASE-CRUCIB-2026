/**
 * CrucibAI TypeScript SDK — native fetch, zero runtime dependencies.
 */

export interface CrucibAIOptions {
  apiKey: string;
  baseUrl?: string;
  timeout?: number;
}

export interface ListingsParams {
  kind?: 'plugin' | 'skill' | 'template' | 'mcp';
}

export interface CreateRunParams {
  prompt: string;
  threadId?: string;
  mode?: 'build' | 'analyze_only' | 'plan_first' | 'one_pass';
}

export interface ApiResponse {
  [key: string]: unknown;
}

class RunsNamespace {
  constructor(private readonly client: CrucibAI) {}

  /** POST /api/runs/{threadId}/preview-loop */
  async create(params: CreateRunParams): Promise<ApiResponse> {
    const tid = params.threadId ?? 'default';
    return this.client._post(`/api/runs/${tid}/preview-loop`, {
      url: 'https://localhost',
      dry_run: true,
      _prompt: params.prompt,
      _mode: params.mode ?? 'build',
    });
  }
}

class BenchmarksNamespace {
  constructor(private readonly client: CrucibAI) {}

  /** GET /api/benchmarks/latest */
  async latest(): Promise<ApiResponse> {
    return this.client._get('/api/benchmarks/latest');
  }
}

class MarketplaceNamespace {
  constructor(private readonly client: CrucibAI) {}

  /** GET /api/marketplace/listings */
  async listings(params?: ListingsParams): Promise<ApiResponse> {
    const qs = params?.kind ? `?kind=${encodeURIComponent(params.kind)}` : '';
    return this.client._get(`/api/marketplace/listings${qs}`);
  }
}

export class CrucibAI {
  private readonly baseUrl: string;
  private readonly headers: Record<string, string>;

  readonly runs: RunsNamespace;
  readonly benchmarks: BenchmarksNamespace;
  readonly marketplace: MarketplaceNamespace;

  constructor(options: CrucibAIOptions) {
    this.baseUrl = (options.baseUrl ?? 'https://api.crucibai.com').replace(/\/$/, '');
    this.headers = {
      Authorization: `Bearer ${options.apiKey}`,
      'Content-Type': 'application/json',
    };
    this.runs = new RunsNamespace(this);
    this.benchmarks = new BenchmarksNamespace(this);
    this.marketplace = new MarketplaceNamespace(this);
  }

  async _get(path: string): Promise<ApiResponse> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method: 'GET',
      headers: this.headers,
    });
    if (!res.ok) {
      throw new Error(`CrucibAI API error ${res.status}: ${await res.text()}`);
    }
    return res.json() as Promise<ApiResponse>;
  }

  async _post(path: string, body: Record<string, unknown>): Promise<ApiResponse> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      throw new Error(`CrucibAI API error ${res.status}: ${await res.text()}`);
    }
    return res.json() as Promise<ApiResponse>;
  }
}
