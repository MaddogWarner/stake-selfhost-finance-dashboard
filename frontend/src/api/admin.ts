import { api } from './client';
import type { ApiUsage, AppSettings, StakeStatus } from '../types';

export async function fetchUsage() {
  const response = await api.get<ApiUsage>('/api/admin/usage');
  return response.data;
}

export async function fetchSettings(): Promise<AppSettings> {
  const response = await api.get<AppSettings>('/api/admin/settings');
  return response.data;
}

export async function updateSettings(settings: Partial<AppSettings>): Promise<AppSettings> {
  const response = await api.post<AppSettings>('/api/admin/settings', settings);
  return response.data;
}

export async function fetchStakeStatus(): Promise<StakeStatus> {
  const response = await api.get<StakeStatus>('/api/admin/stake-status');
  return response.data;
}

export async function setStakeToken(token: string): Promise<StakeStatus> {
  const response = await api.post<StakeStatus>('/api/admin/stake-token', { token });
  return response.data;
}
