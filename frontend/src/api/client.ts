import axios from 'axios';

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000',
  timeout: 20_000,
  withCredentials: true,
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const url = String(error.config?.url ?? '');
    if (error.response?.status === 401 && !url.includes('/auth/')) {
      window.dispatchEvent(new Event('stake-auth-required'));
    }
    return Promise.reject(error);
  },
);
