import { api } from './client';
import type { Exchange, Quote } from '../types';

export async function fetchPrice(ticker: string, exchange: Exchange) {
  const response = await api.get<Quote>(`/api/prices/${ticker}`, { params: { exchange } });
  return response.data;
}
