# API Compute Credit Marketplace

Phase 1 backend MVP: users spend internal platform credits (1 USD = 1,000,000 credits) to run LLM calls through a master DeepSeek API key.

## Stack

- FastAPI + httpx (async proxy)
- PostgreSQL / Supabase (`sql/schema.sql`)
- asyncpg connection pool and row-level wallet locks

## Quick start

```bash
cp .env.example .env
# set DEEPSEEK_API_KEY
docker compose up -d
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Demo user from `sql/seed.sql`:

```
X-Platform-User-Id: 00000000-0000-0000-0000-000000000001
```

```bash
curl -s http://localhost:8000/wallet/balance \
  -H "X-Platform-User-Id: 00000000-0000-0000-0000-000000000001"

curl -s http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "X-Platform-User-Id: 00000000-0000-0000-0000-000000000001" \
  -d '{"model":"deepseek-reasoner","messages":[{"role":"user","content":"Hello"}]}'
```

Successful completions include `X-Credits-Deducted` (and `X-Credits-Remaining`). Failed upstream calls never debit the wallet.

## Credit math

DeepSeek R1 list price, then a 20% platform markup, rounded up to a whole credit:

- input: 0.55 credits/token
- output: 2.19 credits/token

Pre-flight: HTTP 402 unless `credit_balance > 1000`.

## Tests

```bash
pytest
```
