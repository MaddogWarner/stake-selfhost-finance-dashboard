import { api } from './client';
import type { Exchange, Holding, WatchlistItem } from '../types';

const exchangeParam = (exchange?: Exchange) => (exchange ? { exchange } : undefined);

export async function fetchHoldings(exchange?: Exchange) {
  const response = await api.get<Holding[]>('/api/holdings', { params: exchangeParam(exchange) });
  return response.data;
}

export async function fetchWatchlist(exchange?: Exchange) {
  const response = await api.get<WatchlistItem[]>('/api/watchlist', { params: exchangeParam(exchange) });
  return response.data;
}

export async function syncStake() {
  const response = await api.post<{ synced: boolean }>('/api/sync');
  return response.data;
}
