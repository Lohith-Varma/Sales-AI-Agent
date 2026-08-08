# Pay-in-3 Sales Copilot frontend

Production-oriented Next.js 15 App Router frontend for the repository's core API and structured AI copilot service.

## Run locally

```powershell
npm install
Copy-Item .env.example .env.local
npm run dev
```

The defaults expect the core FastAPI service on `http://127.0.0.1:8000` and the AI service on `http://127.0.0.1:8001`. Update `.env.local` when those services run elsewhere.

## Environment

- `CORE_API_URL`: server-side URL used by the same-origin `/api/core/*` proxy.
- `AI_API_URL`: server-side URL used by the same-origin `/api/ai/*` proxy.
- `NEXT_PUBLIC_AI_WS_URL`: browser URL for the structured copilot WebSocket.

The backend uses native WebSockets, not Socket.IO. The frontend deliberately follows that committed protocol.

## Quality checks

```powershell
npm run typecheck
npm run lint
npm run build
npm audit
```

`npm run generate:api` can regenerate OpenAPI types after both FastAPI services are running. Checked-in contract types remain the source of truth when the services are offline.

## Connected backend workflow

Customer profiles, calls, consent, transcript persistence, AI insights, product knowledge, KYC, follow-ups, tasks, sales, dashboard metrics, analytics, notifications, reporting, and call history use the SQL-backed core contracts. Microphone PCM16 streaming, text analysis, RAG citations, compliance, next action, reconnect recovery, and post-call CRM generation use the structured AI service. Authentication is enforced when `AUTH_REQUIRED=true`; development mode is intentionally explicit when the bypass is active.

See [the frontend architecture review](../docs/frontend-architecture-review.md) for the current route map and event boundaries.
