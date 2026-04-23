-- Brain repair / retry metadata persisted on job_steps (runtime_engine.update_step_state)
ALTER TABLE job_steps ADD COLUMN IF NOT EXISTS brain_strategy TEXT;
ALTER TABLE job_steps ADD COLUMN IF NOT EXISTS brain_explanation TEXT;
ALTER TABLE job_steps ADD COLUMN IF NOT EXISTS workspace_fixed BOOLEAN DEFAULT FALSE;
ALTER TABLE job_steps ADD COLUMN IF NOT EXISTS files_repaired TEXT;
ALTER TABLE job_steps ADD COLUMN IF NOT EXISTS brain_mutations_json TEXT DEFAULT '{}';

