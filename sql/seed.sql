-- Demo user for local development. Safe to re-run.
INSERT INTO users (id, email)
VALUES ('00000000-0000-0000-0000-000000000001', 'demo@marketplace.local')
ON CONFLICT (email) DO NOTHING;

INSERT INTO wallets (user_id, credit_balance)
VALUES ('00000000-0000-0000-0000-000000000001', 5_000_000)
ON CONFLICT (user_id) DO NOTHING;
