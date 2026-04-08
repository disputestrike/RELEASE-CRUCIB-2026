-- Migration: Add failure_reason column to jobs table
-- Purpose: Store detailed failure information for job state tracking

ALTER TABLE jobs ADD COLUMN IF NOT EXISTS failure_reason TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS blocked_steps TEXT DEFAULT '[]';

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_jobs_failure_reason ON jobs(failure_reason);

-- Update any existing failed jobs
UPDATE jobs SET failure_reason = 'Job failed - reason not captured' WHERE status = 'failed' AND failure_reason IS NULL;

