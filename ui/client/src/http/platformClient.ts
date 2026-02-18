import axios from 'axios';

/**
 * Axios instance for the platform-backend (admin config, cross-cutting concerns).
 * Proxied via /api4 -> http://127.0.0.1:8003/api
 */
export const platformApi = axios.create({
  baseURL: '/api4',
  timeout: 20000,
  withCredentials: true,
});

platformApi.interceptors.request.use(
  (config) => {
    config.withCredentials = true;
    return config;
  },
  (error) => Promise.reject(error),
);

platformApi.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('Platform API Error:', error);

    let errorMsg = 'Failed to fetch data. Please try again.';
    const errorData = error.response?.data as { error?: string };
    if (errorData?.error) {
      errorMsg = errorData.error;
    }

    return Promise.reject(new Error(errorMsg));
  },
);
