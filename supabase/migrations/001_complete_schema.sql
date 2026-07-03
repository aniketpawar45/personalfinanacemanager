-- 1. Create Identity & Access Management Table
CREATE TABLE IF NOT EXISTS app_users (
    telegram_id TEXT PRIMARY KEY,
    role TEXT CHECK (role IN ('user', 'admin')) DEFAULT 'user',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Enable Row Level Security
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE categories ENABLE ROW LEVEL SECURITY;

-- 3. Security Policies
-- Categories are readable by everyone
CREATE POLICY "Categories are readable by everyone" 
ON categories FOR SELECT USING (true);

-- Users can only insert their own transactions
CREATE POLICY "Users can insert their own transactions" 
ON transactions FOR INSERT WITH CHECK (
    user_id = current_setting('request.jwt.claims', true)::json->>'sub' 
    OR user_id = current_setting('app.telegram_user_id', true)
);

-- Users can only read their own personal transactions (Standard View)
CREATE POLICY "Users can view their own transactions" 
ON transactions FOR SELECT USING (
    user_id = current_setting('app.telegram_user_id', true)
);

-- 4. High-Performance RPC for Personal Stats
CREATE OR REPLACE FUNCTION get_user_statistics(p_user_id text)
RETURNS TABLE (category_name text, total_spent numeric) AS $$
BEGIN
  RETURN QUERY
  SELECT c.category_name::text, SUM(t.amount)::numeric
  FROM transactions t
  LEFT JOIN categories c ON t.category_id = c.id
  WHERE t.user_id = p_user_id
  GROUP BY c.category_name
  ORDER BY SUM(t.amount) DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 5. High-Performance RPC for Global Ledger (Admin Only)
CREATE OR REPLACE FUNCTION get_global_statistics()
RETURNS TABLE (category_name text, total_spent numeric) AS $$
BEGIN
  RETURN QUERY
  SELECT c.category_name::text, SUM(t.amount)::numeric
  FROM transactions t
  LEFT JOIN categories c ON t.category_id = c.id
  GROUP BY c.category_name
  ORDER BY SUM(t.amount) DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


INSERT INTO app_users (telegram_id, role) VALUES ('7511999971', 'admin');

-- ENTERPRISE MIGRATION: Add remarks column for raw input preservation
ALTER TABLE transactions
ADD COLUMN IF NOT EXISTS remarks TEXT DEFAULT '';

CREATE TABLE IF NOT EXISTS report_schedules (
    id SERIAL PRIMARY KEY,
    telegram_id TEXT NOT NULL,
    frequency TEXT NOT NULL CHECK (frequency IN ('daily', 'weekly', 'monthly', 'yearly')),
    scheduled_hour INTEGER DEFAULT 9, -- IST Hour (9 = 09:00 AM)
    emails TEXT NOT NULL, -- Comma separated
    last_sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS for security isolation
ALTER TABLE report_schedules ENABLE ROW LEVEL SECURITY;