# Frontend architecture review

## Scope and source of truth

This review was completed before the Next.js frontend implementation. The repository contains two independent FastAPI applications and an existing Vite proof of concept:

- `ai/`: the structured Pay-in-3 copilot service. It exposes versioned copilot HTTP contracts and a native WebSocket protocol.
- `backend/`: the SQLAlchemy-backed customer, call, consent, transcript, wrap-up, and clause service. It also exposes a second native WebSocket protocol backed by mock STT, LLM, and TTS providers.
- `frontend/`: a small Vite prototype that calls only part of `backend/`, contains placeholder auth/chat clients, and does not implement the requested product shell or product areas.

The frontend will not add or modify backend routes. Missing backend capabilities are surfaced as explicit unavailable states and listed below rather than represented by fabricated data.

## Backend capability map

### Structured copilot service (`ai/`)

Default HTTP prefix: `/api/v1`. Default WebSocket path: `/ws/copilot`.

| Contract | Request | Response/event | Frontend use |
| --- | --- | --- | --- |
| `GET /health` | none | service status, version, environment | global service health and reconnect UI |
| `GET /ready` | none | service status plus Chroma dependency | Admin system health |
| `POST /api/v1/copilot/sessions` | sales agent ID, optional lead ID/language/audio config | session ID, WebSocket path, expiry | accessible text-mode and session bootstrap |
| `POST /api/v1/copilot/analyze-text` | session ID, sequence, customer utterance | complete `CopilotResult` | text fallback for Live Call and keyboard-accessible testing |
| `POST /api/v1/knowledge/ingest` | multipart file plus optional title/version | document and indexed chunk counts | Knowledge Base/Admin upload flow |
| `WS /ws/copilot` | first `session_start`, then PCM16 bytes or `audio_config`, `utterance_end`, `call_end`, `ping` controls | `session_ready`, `transcript`, `copilot_result`, `crm_summary`, `status`, `error`, `pong` | realtime transcript, copilot, post-call CRM, connection health |

The complete live copilot payload provides:

- latest transcript, intent, sentiment, and aggregate/per-agent confidence;
- evidence-backed customer entities (salary, age, city, occupation, loan amount, employment type, and name);
- retrieved knowledge chunks with source, title, section/page, and relevance score;
- grounded suggested response with citations, fallback state, and human-review state;
- next-best action, rationale, confidence, optional follow-up date, and confirmation requirement;
- guardrail safety/grounding decisions, claim checks, violations, and issues.

The post-call event provides a reviewed CRM draft with summary, deterministic lead score and factor breakdown, lead temperature/status, concern, notes, and optional follow-up date.

### Core sales service (`backend/`)

Default HTTP prefix: `/api`. Default WebSocket path: `/ws/calls/{call_id}`.

| Contract | Request | Response/event | Frontend use |
| --- | --- | --- | --- |
| `GET /` | none | service/version | diagnostics |
| `GET /api/health` | none | status/environment/time | global service health |
| `POST /api/customers` | query parameters: name, phone number, optional email/salary | created customer ID/name/phone | CRM create form |
| `GET /api/customers/{customer_id}` | path ID | customer profile, KYC fields, interactions | CRM detail and Live Call customer panel |
| `POST /api/calls` | query customer ID and direction | call ID/status/direction | Live Call bootstrap |
| `POST /api/consent` | query call ID, consent, optional IP | consent ID and call status | mandatory DPDP gate before core voice streaming |
| `GET /api/calls/{call_id}/transcripts` | path ID | decrypted transcript segments | Call History detail |
| `POST /api/calls/{call_id}/wrap-up` | JSON summary and outcome | accepted wrap-up | post-call completion |
| `GET /api/clauses` | none | approved product/eligibility/KYC/disclosure clauses | Knowledge Base and live references |
| `WS /ws/calls/{call_id}` | binary audio or Twilio media frames | JSON `transcript`/`response`, binary synthesized audio, or error | legacy/core call stream compatibility |

The database models are Customer, AgentSession, Call, Transcript, ProductOffer, KYCDoc, FollowUp, and ConsentLog. Several models do not have corresponding API routes.

## Important contract inconsistencies

1. The two FastAPI applications are separate processes but both default to port 8000. They need distinct deployment URLs or ports.
2. The services expose native WebSockets, not Socket.IO. `socket.io-client` cannot connect to either protocol. The frontend will use a typed native WebSocket adapter and will not pretend the transport is Socket.IO.
3. The structured copilot WebSocket creates its own in-memory session and is not linked to the SQL-backed core call/consent record. The frontend tracks both IDs in one call workspace but cannot make them a single backend transaction.
4. The core service CORS list contains only Vite port 5173, while the structured service also allows Next.js port 3000. Next.js HTTP access to the core service therefore needs same-origin server proxies or an updated backend allowlist.
5. The core WebSocket response omits a confidence value even though the current Vite frontend reads one.
6. Core customer lookup falls back to or auto-creates a demo customer for malformed or missing IDs. A production frontend cannot distinguish this fallback from an exact match.
7. Core create-customer and consent inputs are query parameters, while wrap-up is JSON. Generated clients must preserve that distinction.
8. The structured service stores active conversations only in process memory. Refreshes, restarts, or horizontal scaling lose active session state.
9. Knowledge ingestion accepts title/version, while the unused `IngestDocumentsRequest` schema also declares replace behavior, tags, and attributes that the route does not accept.
10. The core mock FAQ claims a fixed 2% monthly late fee, while the core clause endpoint explicitly says to quote only the current approved policy. The UI must prefer approved clause and structured guardrail output and flag the mock response as requiring verification.
11. Neither backend exposes an authentication dependency, token validation, authorization, roles, or permissions. The existing frontend auth client points to routes that do not exist.

## Missing APIs required by the requested product

### Identity and authorization

- Login, logout, refresh, current user, password recovery, session revocation.
- User list/create/update/deactivate, roles, permissions, and backend-enforced Admin access.

### Dashboard, analytics, and reports

- Metric aggregates, conversion funnel, daily calls, agent performance, lead status, sales pipeline, activity, recommendations, forecasting, and rankings.
- Analytics time-series/dimensions and CSV, Excel, or PDF export jobs/downloads.

### CRM and customer profile

- Paginated/filterable lead list and lead update/stage/assignment APIs.
- Notes, tasks, documents, tags, purchases, EMI eligibility, complete KYC status, lead score, and customer timeline APIs.
- A strict not-found response for unknown customer IDs.

### Calls

- Active-call list, call-history list/detail, recording URL/stream, summary, objection timeline, intent timeline, compliance score, agent score, sentiment timeline, and replay markers.
- Agent transcript ingestion, bookmark persistence, note autosave, talking ratio, buying signals, objections, and risk factors.

### Agent actions

- WhatsApp/SMS/email send, follow-up scheduling, KYC workflow link/launch, note creation, close deal, transfer, escalation, and undo endpoints.

### Knowledge management

- Knowledge document list/detail/search/category/pin/update/delete/version/status endpoints.

### Work management and operations

- Tasks CRUD/Kanban/calendar, follow-ups CRUD/timeline/reminders, notifications, user preferences, integration configuration, voice settings, audit logs, and system analytics.
- Realtime CRM, analytics, notification, task, and follow-up events.

## Frontend architecture

The Vite proof of concept will be migrated in place to Next.js 15 App Router with React 19 and strict TypeScript.

```text
frontend/
  app/
    (workspace)/
      dashboard/
      live-calls/
      call-history/
      crm/
      knowledge-base/
      analytics/
      tasks/
      follow-ups/
      reports/
      settings/
      admin/
  components/
    ui/                 shared shadcn-style primitives
    shell/              sidebar, navbar, command palette
    states/             loading, empty, error, offline, unavailable
  features/
    calls/ crm/ copilot/ dashboard/ knowledge/ settings/ system/
  lib/
    api/                generated contracts, fetch clients, errors
    realtime/           typed native WebSocket protocols/reconnect logic
    query/              React Query client and keys
    stores/             Zustand UI/call workspace state
    validation/         forms and runtime contract guards
  types/
```

### Data and state boundaries

- React Query owns remote server state, caching, retries, cancellation, invalidation, and optimistic updates only for endpoints that exist.
- Zustand owns sidebar state, command palette, live call workspace state, transcript bookmarks, and device-local preferences.
- React Hook Form owns forms and validation. Backend validation errors are normalized into field and form errors.
- HTTP calls go through same-origin Next.js route handlers so the core backend's current CORS limitation does not leak into the browser.
- The realtime layer uses discriminated TypeScript unions derived from the Pydantic WebSocket contracts, bounded exponential reconnect, heartbeat, offline state, and duplicate sequence protection.
- Pages without backend support render a polished capability-unavailable state that names the required contract; they do not show fabricated analytics or customer data.

## Screen mapping

| Screen | Available implementation | Explicitly unavailable until backend exists |
| --- | --- | --- |
| Dashboard | health/readiness cards and live service state | all business metrics and charts |
| Live Calls | customer detail, core call creation, consent gate, typed transcript/copilot/CRM events, grounded sources, guardrails, next action, text accessibility mode, wrap-up | external actions, persisted notes/bookmarks, buying signals/objections/talking ratio |
| Call History | exact call-ID transcript lookup and wrap-up | list, recording, scores, timelines, summaries |
| CRM | create customer and exact-ID detail lookup | lead list/filtering, edit, assignment, notes/tasks/documents |
| Knowledge Base | clauses, search over loaded clauses, document ingestion | document catalog/pinning/version management |
| Analytics/Reports | service health only | business analytics, forecasts, exports |
| Tasks/Follow Ups | route and contract-aware unavailable state | all records and mutations |
| Settings | device-local UI and AI display preferences | server profile, integrations, voice/security persistence |
| Admin | readiness, dependency health, knowledge ingestion | user/role/permission/log/analytics management |

## Incremental implementation and verification gates

1. Foundation: Next.js shell, design tokens, accessible navigation, command palette, responsive behavior, query/error infrastructure, typed clients, and capability registry. Verify TypeScript, lint, build, route rendering, keyboard focus, and mobile shell.
2. Dashboard and CRM: implement only health, create, and exact lookup workflows. Verify success, loading, empty, invalid input, backend error, offline, and retry states.
3. Live Call: implement core call/consent lifecycle, transcript tools, notes, and post-call workspace. Verify WebSocket state transitions, cleanup, reconnect, ordering, call end, and consent blocking.
4. AI Copilot: map every `CopilotResult` and CRM summary field to accessible cards, citations, risk/guardrail states, and confidence. Verify schema parsing and fallback/human-review behavior.
5. Analytics and Reports: ship capability-aware routes without invented data; wire any discovered health data only.
6. Settings and Admin: local preference settings, system health, and knowledge upload; explicitly gate absent RBAC/operations.
7. Polish: screen-reader labels, focus management, reduced motion, responsive layouts, virtualized transcript, code splitting, query caching, hydration safety, and runtime error boundaries.

The final verification must keep backend limitations separate from frontend correctness. A passing frontend build cannot prove unavailable backend workflows or authenticate a user when the repository provides no authentication contract.

## Implementation status

All seven frontend phases are implemented. The former Vite proof of concept has been replaced by the Next.js 15 application described above. Available backend flows use the committed HTTP and native WebSocket contracts; unsupported product areas remain visible, navigable, and explicit about the contract they require.

Final verification covered strict TypeScript, zero-warning lint, production build, dependency audit, every route at desktop and mobile widths, keyboard command navigation, theme persistence, landmark/control-label checks, hydration/runtime logs, and a contract-faithful browser flow from customer lookup through consent, AI analysis, transcript rendering, post-call CRM summary, and core wrap-up. Microphone permission was not granted during automation; the browser audio path is implemented with an AudioWorklet that emits the service-required mono 16 kHz PCM16 frames.

Sites publishing was intentionally not attempted: this repository currently produces a standard Next.js server build rather than the required Cloudflare Workers-compatible `dist/server/index.js`, and no public core/AI HTTP or WebSocket origins were supplied. Publishing the shell alone would create a non-functional production deployment.
