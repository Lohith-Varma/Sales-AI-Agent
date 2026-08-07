import { apiClient } from './axios';
import type { CrmRecord, Clause } from '../types';
import type { StandardResponse } from './sales';

export const dashboardApi = {
  /**
   * Retrieves a customer profile by ID, including KYC fields and past interactions.
   */
  async getCustomer(customerId: string): Promise<StandardResponse<CrmRecord>> {
    const response = await apiClient.get(`/api/customers/${customerId}`);
    return response.data;
  },

  /**
   * Retrieves compliance and product clauses (RAG knowledge base items).
   */
  async getClauses(): Promise<StandardResponse<Clause[]>> {
    const response = await apiClient.get(`/api/clauses`);
    return response.data;
  },
};
