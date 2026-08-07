/*
 * TypeScript mirrors of the currently committed FastAPI/Pydantic contracts.
 * The repository cannot generate OpenAPI without the Python runtime dependencies,
 * so `npm run generate:api` is provided to refresh types from running services.
 */

export interface StandardResponse<T> {
  success: boolean;
  message: string;
  data: T;
}

export interface CoreHealth {
  status: string;
  env: string;
  timestamp: string;
}

export interface CoreCustomer {
  id: string;
  name: string;
  email: string | null;
  phone: string;
  city: string;
  sensitiveDataOnFile: boolean;
  kycFields: Array<{ label: string; value: string }>;
  interactions: Array<{ date: string; outcome: string; note: string }>;
}

export interface CoreClause {
  id: string;
  title: string;
  topic: string;
  body: string;
  source: string;
  lastSynced: string;
  stale?: boolean;
}

export interface CoreTranscript {
  speaker: "customer" | "agent" | "ai" | string;
  text: string;
  timestamp: string;
  confidence: number | null;
}

export interface CoreCallCreated {
  call_id: string;
  status: string;
  direction: "inbound" | "outbound" | string;
}

export interface CoreConsent {
  consent_id: string;
  consent_given: boolean;
  call_status: string;
}

export interface CoreWrapUp {
  call_id: string;
  summary: string;
  outcome: string;
}

export type IntentType =
  | "product_inquiry"
  | "eligibility"
  | "pricing"
  | "kyc"
  | "objection"
  | "existing_loan"
  | "interested"
  | "follow_up"
  | "rejection"
  | "unknown";

export type SentimentType = "positive" | "neutral" | "negative" | "frustrated" | "confused" | "unknown";
export type NextActionType = "explain_benefits" | "explain_kyc" | "schedule_follow_up" | "transfer_to_human_expert" | "send_product_brochure" | "start_application" | "address_objection" | "ask_clarifying_question" | "no_action";
export type LeadStatus = "new" | "qualifying" | "interested" | "follow_up_required" | "application_ready" | "not_interested" | "disqualified" | "escalation_required";
export type LeadTemperature = "cold" | "warm" | "hot";
export type WorkflowStage = "received" | "transcribing" | "analyzing" | "retrieving" | "generating" | "validating" | "summarizing" | "completed" | "failed";

export interface TextEvidence {
  text: string;
  start_character: number | null;
  end_character: number | null;
}

export interface ExtractedEntity<T> {
  value: T;
  confidence: number;
  evidence: TextEvidence;
}

export interface MoneyAmount { amount: string | number; currency: string }

export interface CustomerEntities {
  salary: ExtractedEntity<MoneyAmount> | null;
  age: ExtractedEntity<number> | null;
  city: ExtractedEntity<string> | null;
  occupation: ExtractedEntity<string> | null;
  loan_amount: ExtractedEntity<MoneyAmount> | null;
  employment_type: ExtractedEntity<string> | null;
  customer_name: ExtractedEntity<string> | null;
}

export interface RetrievedChunk {
  chunk_id: string;
  document_id: string;
  text: string;
  source: string;
  title: string;
  page_number: number | null;
  section: string | null;
  relevance_score: number;
}

export interface GroundedClaim { claim: string; citation_chunk_ids: string[] }

export interface SuggestedResponse {
  text: string;
  grounded_claims: GroundedClaim[];
  citation_chunk_ids: string[];
  is_fallback: boolean;
  requires_human_review: boolean;
  confidence: number;
}

export interface NextActionRecommendation {
  action: NextActionType;
  rationale: string;
  confidence: number;
  suggested_follow_up_date: string | null;
  requires_confirmation: boolean;
}

export interface GuardrailViolation {
  violation_type: string;
  severity: "warning" | "error" | "critical";
  message: string;
  claim: string | null;
}

export interface ClaimGroundingCheck {
  claim: string;
  cited_chunk_ids: string[];
  supported_chunk_ids: string[];
  is_supported: boolean;
  support_score: number;
}

export interface GuardrailOutput {
  is_safe: boolean;
  is_grounded: boolean;
  valid_json: boolean;
  contains_unsupported_financial_advice: boolean;
  grounding_coverage: number;
  claim_checks: ClaimGroundingCheck[];
  violations: GuardrailViolation[];
  requires_human_review: boolean;
  final_response: SuggestedResponse;
}

export interface AgentConfidenceScores {
  intent: number;
  sentiment: number;
  entities: number;
  retrieval: number;
  response: number;
  next_action: number;
}

export interface WorkflowIssue {
  stage: WorkflowStage;
  code: string;
  message: string;
  recoverable: boolean;
}

export interface LeadScore {
  score: number;
  temperature: LeadTemperature;
  factors: Array<{ name: string; points: number; rationale: string }>;
}

export interface CRMSummary {
  call_summary: string;
  lead_score: LeadScore;
  follow_up_date: string | null;
  customer_concern: string | null;
  lead_status: LeadStatus;
  important_notes: string[];
  generated_at: string;
}

export interface CopilotResult {
  schema_version: "1.0";
  request_id: string;
  session_id: string;
  sequence_number: number;
  latest_transcript: string;
  intent: IntentType;
  sentiment: SentimentType;
  entities: CustomerEntities;
  retrieved_context: RetrievedChunk[];
  suggested_response: SuggestedResponse;
  next_best_action: NextActionRecommendation;
  crm_summary: CRMSummary | null;
  guardrail: GuardrailOutput;
  confidence: number;
  agent_confidences: AgentConfidenceScores;
  issues: WorkflowIssue[];
  generated_at: string;
}

export interface AudioConfiguration {
  encoding: "pcm_s16le";
  sample_rate_hz: number;
  channels: 1 | 2;
  sample_width_bytes: 2;
}

export interface TranscriptSegment {
  segment_id: string;
  speaker: "customer" | "sales_agent" | "unknown";
  text: string;
  start_seconds: number;
  end_seconds: number;
  confidence: number | null;
  language: string;
  is_final: boolean;
}

export interface ServiceHealth {
  status: "healthy" | "degraded" | "unavailable";
  service: string;
  version: string;
  environment: string;
  dependencies: Record<string, { status: "healthy" | "degraded" | "unavailable"; detail?: string | null }>;
  checked_at: string;
}

export interface SessionCreated {
  session_id: string;
  websocket_path: string;
  expires_at: string;
}

export interface IngestionResult {
  source: string;
  document_count: number;
  chunk_count: number;
  skipped_unchanged_count: number;
  collection_name: string;
  completed_at: string;
}

export type AIServerEvent =
  | { type: "session_ready"; session_id: string; audio_config: AudioConfiguration; created_at: string }
  | { type: "transcript"; session_id: string; sequence_number: number; segments: TranscriptSegment[] }
  | { type: "copilot_result"; result: CopilotResult }
  | { type: "crm_summary"; session_id: string; crm_summary: CRMSummary; requires_human_review: boolean }
  | { type: "status"; session_id: string; stage: WorkflowStage; message: string }
  | { type: "error"; code: string; message: string; request_id: string | null; retryable: boolean }
  | { type: "pong"; nonce: string };

export type AIClientControlMessage =
  | { type: "session_start"; sales_agent_id: string; external_lead_id?: string; language?: string; audio_config?: AudioConfiguration }
  | { type: "audio_config"; audio_config: AudioConfiguration }
  | { type: "utterance_end"; sequence_number: number }
  | { type: "call_end"; ended_at?: string }
  | { type: "ping"; nonce: string };

export type CoreSocketEvent =
  | { event: "transcript"; speaker: string; text: string; confidence?: number | null }
  | { event: "response"; speaker: "ai"; text: string; citations: string[]; escalate: boolean }
  | { error: string };
