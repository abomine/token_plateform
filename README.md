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
2. Add a **PostgreSQL** plugin in the **same project**.
3. Open the **web** service → **Variables**:
   - Remove any `DATABASE_URL` copied from `.env.example` (that points at localhost and will crash startup).
   - Add a reference to Postgres, for example:
     - `DATABASE_URL=${{Postgres.DATABASE_URL}}`
     - or `DATABASE_PRIVATE_URL=${{Postgres.DATABASE_PRIVATE_URL}}`
   - Set `DEEPSEEK_API_KEY` (required)
   - Optional: `PLATFORM_API_KEY`, `MIN_PREFLIGHT_CREDITS=1000`
4. Redeploy. Schema is applied **at app startup**.
5. Open `GET /health` — if `database` is `not_ready`, your `DATABASE_URL` still points at localhost; fix the variable (see below) and redeploy again.

### Where to run `python -m backend.migrate`

| When | Where |
| --- | --- |
| Normal deploy | Nowhere — startup applies schema + demo seed (`SEED_DEMO_USER=true` by default) |
| Manual seed in Railway shell | `/opt/venv/bin/python -m backend.migrate --seed` (plain `python` misses the venv) |
| Local | after `docker compose up -d`: `python -m backend.migrate --seed` |

Disable demo seed with `SEED_DEMO_USER=false`.

Do **not** put migrate in a Procfile `release:` line: Nixpacks runs that during the image build, when Postgres is not available.

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
