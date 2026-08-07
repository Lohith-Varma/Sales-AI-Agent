import { apiClient } from './axios';
import type { StandardResponse } from './sales';

export const chatApi = {
  /**
   * Placeholder to send a chat message.
   */
  async sendMessage(message: string, context?: any): Promise<StandardResponse<any>> {
    const response = await apiClient.post('/api/chat/messages', { message, context });
    return response.data;
  },
};
