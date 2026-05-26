import { api } from './client';
import type { ApiUsage, AppSettings } from '../types';

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
