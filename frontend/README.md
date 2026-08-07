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
- `NEXT_PUBLIC_CORE_WS_URL`: browser URL for the core call WebSocket.
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

## Backend capability boundary

The implemented customer lookup/create, call creation, consent, transcript, wrap-up, knowledge clauses/ingestion, health, AI text analysis, microphone PCM16 streaming, and realtime copilot flows use real backend contracts. Screens that require absent aggregate/list/auth/role/task/follow-up/report/integration APIs show explicit unavailable states instead of fabricated records.

See [the frontend architecture review](../docs/frontend-architecture-review.md) for the route map, event schemas, implementation phases, and missing backend contracts.
