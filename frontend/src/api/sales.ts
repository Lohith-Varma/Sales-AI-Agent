import { apiClient } from './axios';
import type { TranscriptLine } from '../types';

export interface StandardResponse<T> {
  success: boolean;
  message: string;
  data: T;
}

export interface InitiateCallData {
  call_id: string;
  status: string;
  direction: string;
}

export interface LogConsentData {
  consent_id: string;
  consent_given: boolean;
  call_status: string;
}

export interface WrapUpData {
  call_id: string;
  summary: string;
  outcome: string;
}

export const salesApi = {
  /**
   * Initiates a new call session for a customer.
   */
  async initiateCall(customerId: string, direction = 'inbound'): Promise<StandardResponse<InitiateCallData>> {
    const response = await apiClient.post(`/api/calls?customer_id=${encodeURIComponent(customerId)}&direction=${encodeURIComponent(direction)}`);
    return response.data;
  },

  /**
   * Logs a customer's consent for call recording/AI processing.
   */
  async logConsent(callId: string, consentGiven: boolean, ipAddress?: string): Promise<StandardResponse<LogConsentData>> {
    let url = `/api/consent?call_id=${encodeURIComponent(callId)}&consent_given=${consentGiven}`;
    if (ipAddress) {
      url += `&ip_address=${encodeURIComponent(ipAddress)}`;
    }
    const response = await apiClient.post(url);
    return response.data;
  },

  /**
   * Retrieves transcripts for a specific call.
   */
  async getTranscripts(callId: string): Promise<StandardResponse<{ call_id: string; transcripts: TranscriptLine[] }>> {
    const response = await apiClient.get(`/api/calls/${callId}/transcripts`);
    return response.data;
  },

  /**
   * Completes post-call wrap-up summary and outcome.
   */
  async completeWrapUp(callId: string, summary: string, outcome: string): Promise<StandardResponse<WrapUpData>> {
    const response = await apiClient.post(`/api/calls/${callId}/wrap-up`, {
      summary,
      outcome,
    });
    return response.data;
  },
};
