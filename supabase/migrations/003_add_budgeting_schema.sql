-- Migration: 003_add_budgeting_schema.sql
-- Description: Extends the database schema to handle user budget tracking and currency configurations.

-- 1. Add budget tracking metrics directly onto our user management profile table
ALTER TABLE app_users
ADD COLUMN IF NOT EXISTS monthly_budget_limit NUMERIC DEFAULT 0.0,
ADD COLUMN IF NOT EXISTS preferred_currency TEXT DEFAULT 'INR';

-- 2. Verify that our existing Row-Level Security rules apply to these new configuration updates
ALTER TABLE app_users ENABLE ROW LEVEL SECURITY;