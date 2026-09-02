-- Demo user for local development / Railway seed. Safe to re-run.
INSERT INTO users (id, email)
VALUES ('00000000-0000-0000-0000-000000000001', 'demo@marketplace.local')
ON CONFLICT (email) DO NOTHING;

INSERT INTO wallets (user_id, credit_balance)
VALUES ('00000000-0000-0000-0000-000000000001', 5_000_000)
ON CONFLICT (user_id) DO NOTHING;

INSERT INTO tasks (id, title, description, reward_credits, category, created_by)
VALUES
    (
        '00000000-0000-0000-0000-000000000101',
        'Scrape competitor pricing table',
        'Extract the public pricing rows from three SaaS landing pages into clean JSON.',
        25000,
        'Scraping',
        '00000000-0000-0000-0000-000000000001'
    ),
    (
        '00000000-0000-0000-0000-000000000102',
        'Rewrite onboarding prompt pack',
        'Produce 5 system prompts for a B2B support agent with clear tone constraints.',
        40000,
        'Prompting',
        '00000000-0000-0000-0000-000000000001'
    ),
    (
        '00000000-0000-0000-0000-000000000103',
        'Fix flaky wallet debit race',
        'Reproduce and patch a concurrent credit deduction edge case in the proxy ledger.',
        75000,
        'Bug Fix',
        '00000000-0000-0000-0000-000000000001'
    )
ON CONFLICT (id) DO NOTHING;
