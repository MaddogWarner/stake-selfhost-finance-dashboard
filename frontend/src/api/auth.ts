import { api } from './client';

export type AuthStatus = 'setup_required' | 'unauthenticated' | 'authenticated';

export async function fetchAuthStatus(): Promise<AuthStatus> {
  const response = await api.get<{ status: AuthStatus }>('/api/auth/status');
  return response.data.status;
}

export async function setup(password: string): Promise<AuthStatus> {
  const response = await api.post<{ status: AuthStatus }>('/api/auth/setup', { password });
  return response.data.status;
}

export async function login(password: string): Promise<AuthStatus> {
  const response = await api.post<{ status: AuthStatus }>('/api/auth/login', { password });
  return response.data.status;
}

export async function logout(): Promise<AuthStatus> {
  const response = await api.post<{ status: AuthStatus }>('/api/auth/logout');
  return response.data.status;
}
