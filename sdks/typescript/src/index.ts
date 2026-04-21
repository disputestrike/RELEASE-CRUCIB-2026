/**
 * @crucibai/sdk — Official TypeScript SDK for CrucibAI.
 *
 * Zero runtime dependencies; uses native fetch (Node 18+, all modern browsers).
 */
export { CrucibAI } from './client.js';
export type {
  CrucibAIOptions,
  ListingsParams,
  CreateRunParams,
  ApiResponse,
} from './client.js';
