-- Add speed_tier column to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS speed_tier VARCHAR(20) DEFAULT 'pro';

-- Add index for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_speed_tier ON users(speed_tier);

-- Update existing users to have appropriate speed tier based on plan
UPDATE users SET speed_tier = 'lite' WHERE plan = 'free';
UPDATE users SET speed_tier = 'pro' WHERE plan IN ('starter', 'builder');
UPDATE users SET speed_tier = 'max' WHERE plan IN ('pro', 'teams');

-- Create speed_tier_history table for tracking changes
CREATE TABLE IF NOT EXISTS speed_tier_history (
  id SERIAL PRIMARY KEY,
  user_id VARCHAR(255) NOT NULL,
  old_speed_tier VARCHAR(20),
  new_speed_tier VARCHAR(20) NOT NULL,
  changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_speed_tier_history_user ON speed_tier_history(user_id);
