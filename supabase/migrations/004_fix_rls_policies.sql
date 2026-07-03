-- Migration: 004_fix_rls_policies.sql
-- Description: Optimizes security rules to process user context validation rules.

-- 1. Reset existing transaction write restrictions
DROP POLICY IF EXISTS "Users can insert their own transactions" ON transactions;

-- 2. Build an updated security filter that works perfectly with standard client instances
CREATE POLICY "Users can insert their own transactions" ON transactions FOR INSERT WITH CHECK (
    user_id = current_setting('app.telegram_user_id', true)
    OR user_id = auth.uid()::text
);

-- 3. Reset existing view rules
DROP POLICY IF EXISTS "Users can view their own transactions" ON transactions;

CREATE POLICY "Users can view their own transactions" ON transactions FOR SELECT USING (
    user_id = current_setting('app.telegram_user_id', true)
    OR user_id = auth.uid()::text
);