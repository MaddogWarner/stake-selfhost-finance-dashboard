import { api } from './client';
import type {
  Exchange,
  Holding,
  HoldingCreate,
  HoldingUpdate,
  WatchlistCreate,
  WatchlistItem,
} from '../types';

const exchangeParam = (exchange?: Exchange) => (exchange ? { exchange } : undefined);

export async function fetchHoldings(exchange?: Exchange) {
  const response = await api.get<Holding[]>('/api/holdings', { params: exchangeParam(exchange) });
  return response.data;
}

export async function fetchWatchlist(exchange?: Exchange) {
  const response = await api.get<WatchlistItem[]>('/api/watchlist', { params: exchangeParam(exchange) });
  return response.data;
}

export async function createHolding(payload: HoldingCreate) {
  const response = await api.post<Holding>('/api/holdings', payload);
  return response.data;
}

export async function updateHolding(id: number, payload: HoldingUpdate) {
  const response = await api.patch<Holding>(`/api/holdings/${id}`, payload);
  return response.data;
}

export async function deleteHolding(id: number) {
  const response = await api.delete<{ deleted: boolean }>(`/api/holdings/${id}`);
  return response.data;
}

export async function addWatchlist(payload: WatchlistCreate) {
  const response = await api.post<WatchlistItem>('/api/watchlist', payload);
  return response.data;
}

export async function removeWatchlist(id: number) {
  const response = await api.delete<{ deleted: boolean }>(`/api/watchlist/${id}`);
  return response.data;
}

export async function syncStake() {
  const response = await api.post<{ synced: boolean }>('/api/sync');
  return response.data;
}
