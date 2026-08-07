import { apiClient } from './axios';
import type { StandardResponse } from './sales';

export const authApi = {
  /**
   * Placeholder login endpoint.
   */
  async login(credentials: any): Promise<StandardResponse<{ token: string }>> {
    const response = await apiClient.post('/api/auth/login', credentials);
    return response.data;
  },

  /**
   * Placeholder getCurrentUser endpoint.
   */
  async getCurrentUser(): Promise<StandardResponse<any>> {
    const response = await apiClient.get('/api/auth/me');
    return response.data;
  },
};
