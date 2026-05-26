import { api } from './client';
import type { Exchange, Fundamental } from '../types';

export async function fetchFundamentals(ticker: string, exchange: Exchange) {
  const response = await api.get<Fundamental>(`/api/fundamentals/${ticker}`, { params: { exchange } });
  return response.data;
}
