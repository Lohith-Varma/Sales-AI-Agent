export interface TranscriptLine { id: number; speaker: 'Agent' | 'Customer'; text: string; intent?: string; confidence?: number; topic?: string }
export interface Suggestion { id: string; intent: string; text: string; source: string; confidence: number; createdAt: number; status: 'active' | 'archived' }
export interface Clause { id: string; title: string; topic: string; body: string; source: string; lastSynced: string; stale?: boolean }
export interface CrmRecord { id: string; name: string; email: string; phone: string; city: string; sensitiveDataOnFile: boolean; kycFields: { label: string; value: string }[]; interactions: { date: string; outcome: string; note: string }[] }
