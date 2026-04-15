/**
 * Project Memory — simple key-value store per project
 * Thin wrapper around memoryGraph for project-scoped data
 */
import { memoryGraph } from './memoryGraph';

export async function saveProjectData(projectId, key, value, importance = 0.6) {
  return memoryGraph.save('project', `${projectId}:${key}`, value, importance);
}

export async function getProjectData(projectId, key) {
  const node = await memoryGraph.get('project', `${projectId}:${key}`);
  return node?.content ?? null;
}

export async function searchProjectMemory(query) {
  return memoryGraph.search(query, 'project');
}

export async function saveUserPreference(key, value) {
  return memoryGraph.save('user', key, value, 0.9);
}

export async function getUserPreference(key) {
  const node = await memoryGraph.get('user', key);
  return node?.content ?? null;
}

export async function recordPattern(key, pattern, importance = 0.7) {
  return memoryGraph.save('pattern', key, pattern, importance);
}
