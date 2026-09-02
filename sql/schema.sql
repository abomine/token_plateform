-- API Compute Credit Marketplace — Phase 1 schema (PostgreSQL / Supabase)
-- Credits: 1 USD = 1,000,000 platform credits.
-- Apply with: psql "$DATABASE_URL" -f sql/schema.sql

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       TEXT NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS wallets (
    user_id         UUID PRIMARY KEY REFERENCES users (id) ON DELETE CASCADE,
    credit_balance  BIGINT NOT NULL DEFAULT 0 CHECK (credit_balance >= 0),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'credit_transaction_type') THEN
        CREATE TYPE credit_transaction_type AS ENUM ('purchase', 'task_reward', 'api_usage');
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS credit_transactions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    amount      INTEGER NOT NULL,
    type        credit_transaction_type NOT NULL,
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS api_logs (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    model                   TEXT NOT NULL,
    prompt_tokens           INTEGER NOT NULL CHECK (prompt_tokens >= 0),
    completion_tokens       INTEGER NOT NULL CHECK (completion_tokens >= 0),
    total_credits_deducted  INTEGER NOT NULL CHECK (total_credits_deducted >= 0),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_credit_transactions_user_created
    ON credit_transactions (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_api_logs_user_created
    ON api_logs (user_id, created_at DESC);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'task_category') THEN
        CREATE TYPE task_category AS ENUM ('Scraping', 'Prompting', 'Bug Fix');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'task_status') THEN
        CREATE TYPE task_status AS ENUM ('open', 'completed');
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS tasks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title           TEXT NOT NULL,
    description     TEXT NOT NULL,
    reward_credits  INTEGER NOT NULL CHECK (reward_credits > 0),
    category        task_category NOT NULL,
    status          task_status NOT NULL DEFAULT 'open',
    created_by      UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    completed_by    UUID REFERENCES users (id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_tasks_status_created
    ON tasks (status, created_at DESC);

CREATE OR REPLACE FUNCTION set_wallets_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_wallets_updated_at ON wallets;
CREATE TRIGGER trg_wallets_updated_at
    BEFORE UPDATE ON wallets
    FOR EACH ROW
    EXECUTE FUNCTION set_wallets_updated_at();
