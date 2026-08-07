import axios from 'axios';

// Load base API URL from environment variable or default to localhost:8000
const baseURL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export const apiClient = axios.create({
  baseURL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
});

// Request interceptor to attach JWT Token in headers if present in localStorage
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle unified error mappings and trace HTTP response envelopes
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    console.error('API Error Response:', error);
    
    let message = 'An unexpected error occurred';
    let status = error.response?.status;
    let errors = null;

    if (error.response) {
      // The server responded with a status code that falls out of the range of 2xx
      const data = error.response.data;
      message = data.message || data.detail || message;
      errors = data.errors || null;
      
      // If validation error (422)
      if (status === 422 && Array.isArray(data.detail)) {
        message = data.detail.map((err: any) => `${err.loc.join('.')}: ${err.msg}`).join(', ');
        errors = data.detail;
      }
    } else if (error.request) {
      // The request was made but no response was received
      message = 'Connection timed out or network error. Please check your backend server.';
      status = 0;
    } else {
      // Something happened in setting up the request that triggered an Error
      message = error.message;
    }

    return Promise.reject({
      success: false,
      message,
      status,
      errors,
    });
  }
);
