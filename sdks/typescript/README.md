# @crucibai/sdk

Official TypeScript/JavaScript SDK for [CrucibAI](https://crucibai.com). Zero runtime dependencies.

## Installation

```bash
npm install @crucibai/sdk
```

## Quickstart

```typescript
import { CrucibAI } from '@crucibai/sdk';

const client = new CrucibAI({ apiKey: 'crc_YOUR_KEY_HERE' });

// Browse marketplace templates
const { listings } = await client.marketplace.listings({ kind: 'template' });
for (const l of listings as any[]) {
  console.log(l.title, l.proof_score);
}

// Start a preview-loop run
const run = await client.runs.create({ prompt: 'Build a todo app', mode: 'build' });
console.log(run.run_id, run.status);

// Latest benchmarks
const benchmarks = await client.benchmarks.latest();
console.log(benchmarks);
```

Get your API key from the [Developer Portal](https://crucibai.com/developer).
