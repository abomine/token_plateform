# API Compute Credit Marketplace

Phase 1 backend MVP: users spend internal platform credits (1 USD = 1,000,000 credits) to run LLM calls through a master DeepSeek API key.

## Stack

- FastAPI + httpx (async proxy)
- PostgreSQL / Supabase / Railway Postgres (`sql/schema.sql`)
- asyncpg connection pool and row-level wallet locks

## Quick start (local)

```bash
cp .env.example .env
# set DEEPSEEK_API_KEY
docker compose up -d
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python -m backend.migrate --seed
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

## Deploy on Railway

1. Create a new Railway project from this GitHub repo (`main`).
2. Add a **PostgreSQL** plugin and **link it** to the web service (`DATABASE_URL` must be injected — otherwise the app still points at localhost).
3. Set service variables:
   - `DEEPSEEK_API_KEY` (required)
   - `PLATFORM_API_KEY` (optional shared Bearer secret)
   - `MIN_PREFLIGHT_CREDITS=1000` (optional)
4. Deploy. Schema is applied **at app startup** (`python -m backend.migrate` is not a build step).

### Where to run `python -m backend.migrate`

| When | Where |
| --- | --- |
| Normal deploy | Nowhere — startup applies `sql/schema.sql` automatically |
| Seed demo user | Railway → service → **Shell** / one-off run: `python -m backend.migrate --seed` |
| Local | after `docker compose up -d`: `python -m backend.migrate --seed` |

Do **not** put migrate in a Procfile `release:` line: Nixpacks runs that during the image build, when Postgres is not available (the `127.0.0.1:5432` failure you saw).

Health check: `GET /health`

## Credit math

DeepSeek R1 list price, then a 20% platform markup, rounded up to a whole credit:

- input: 0.55 credits/token
- output: 2.19 credits/token

Pre-flight: HTTP 402 unless `credit_balance > 1000`.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```
