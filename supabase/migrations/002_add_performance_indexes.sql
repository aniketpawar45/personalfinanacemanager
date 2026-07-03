-- Migration: 002_add_performance_indexes.sql
-- Description: Establishes optimal B-Tree indexes for multi-tenant query lookups.

-- 1. Optimize user expense lookups and date-range reporting filters
CREATE INDEX IF NOT EXISTS idx_transactions_user_date
ON transactions(user_id, transaction_date DESC);

-- 2. Optimize join operations during categorical breakdowns
CREATE INDEX IF NOT EXISTS idx_transactions_category_id
ON transactions(category_id);

-- 3. Optimize duplicate transaction detection checks
CREATE INDEX IF NOT EXISTS idx_transactions_duplicate_check
ON transactions(user_id, amount, description, created_at DESC);