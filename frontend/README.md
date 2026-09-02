# ComputeMarket Frontend

Next.js (App Router) + Tailwind dark SPA for the credit marketplace backend.

## Local

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Open http://localhost:3000

`NEXT_PUBLIC_API_URL` should point at your FastAPI host (Railway or local `:8000`).

## Railway

Add a second service from this repo with **Root Directory** = `frontend`, then set:

- `NEXT_PUBLIC_API_URL=https://web-production-84ecb.up.railway.app`
- `NEXT_PUBLIC_USER_ID=00000000-0000-0000-0000-000000000001`

Also set `CORS_ORIGINS` on the API service to your frontend origin (or `*`).
