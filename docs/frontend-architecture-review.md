# Frontend architecture and backend contract map

## Runtime services

- `frontend/` is the Next.js 15 App Router sales workspace on port 3000. Its same-origin route handlers proxy REST traffic to the core and AI services; browser audio uses the AI service's native WebSocket directly.
- `backend/` is the SQLAlchemy/Alembic core on port 8000. It owns customers, users, leads, calls, consent, transcripts, insights, suggestions, KYC, products, purchases, offers, notes, follow-ups, tasks, notifications, dashboards, and analytics.
- `ai/` is the structured FastAPI/LangGraph co-pilot on port 8001. It owns Whisper inference, Gemini agents, Chroma retrieval, guardrails, active audio buffers, and post-call CRM generation. It writes every durable call event through authenticated internal core routes.

The retired mock voice WebSocket is no longer registered by the core application. Production voice and text assistance use only the structured AI protocol.

## Screen-to-data map

| Screen | Durable source |
| --- | --- |
| Live Calls | Core customer/call/consent/note/KYC/follow-up/sale APIs plus AI WebSocket and text analysis |
| CRM | Core customers, call history, purchases, offers, KYC, notes, follow-ups, tags, and live signals |
| Call History | Core calls, encrypted transcripts, summaries, intent, sentiment, compliance, scores, revenue, and recording URLs |
| Knowledge Base | Core ProductOffer clauses and knowledge-document catalog; AI ingestion and Chroma readiness |
| Dashboard | Core database aggregates for calls, conversion, duration, follow-ups, revenue, satisfaction, AI usage, lead funnel, and activity |
| Analytics | Core 30-day database aggregates for call volume, intent, sentiment, duration, funnel, and agent performance |
| Tasks / Follow Ups | Core CRUD routes and the in-process due-item scheduler |
| Reports | Live dashboard and analytics aggregates with client-side CSV export |
| Admin / Settings | Core and AI readiness, database mode, auth posture, authorized users, catalog, and current identity |

## Live protocol

1. The frontend loads a selected CRM customer and creates a core call.
2. DPDP recording and AI-processing consent is persisted before microphone controls are enabled.
3. A `session_start` message links the AI session to the core call ID. When authentication is enabled, the same JWT is verified by both services.
4. PCM16 frames are buffered in bounded windows. `utterance_end` triggers Whisper and the parallel intent, sentiment, and entity fan-out.
5. Approved database products and uploaded documents are embedded in Chroma. Retrieval evidence is passed to response and next-action agents, then guardrails verify every cited product claim.
6. Transcript segments and co-pilot results are written idempotently to the core. The UI de-duplicates by segment ID and supports search, copy, auto-scroll, and persistent bookmarks.
7. Heartbeats run every 15 seconds. A stale socket reconnects with exponential backoff; the new AI session recovers transcript and last-result context from the core call record.
8. `call_end` generates and persists a CRM summary, lead score, notes, and a linked follow-up/task when required. A converted wrap-up creates one idempotent purchase per call, records revenue, accepts the selected database offer, and emits a notification.

## Security and failure behavior

- Production startup rejects disabled authentication or missing JWT/internal-service secrets. User routes enforce administrator roles, and both HTTP and WebSocket AI paths verify access tokens when enabled.
- Sensitive customer fields, transcript text, notes, summaries, and KYC values use the encrypted SQLAlchemy type. Logs contain identifiers and operational metadata instead of raw customer content.
- REST writes validate Pydantic inputs, use UUID not-found checks, and are rate-limited. Cross-service persistence retries with bounded exponential backoff and idempotent segment, sequence, and purchase keys.
- AI timeout, quota, retrieval, or persistence failures produce typed retryable errors or a human-review fallback. No unsupported product claim is shown when approved evidence is unavailable.
- Active audio buffers remain process-local, but all recovery-critical transcript and last-result context is durable in the core database, so reconnects do not lose the call conversation.
