import { api } from './client';
import type { Exchange, NewsItemType } from '../types';

export async function fetchNews(ticker: string, exchange: Exchange) {
  const response = await api.get<NewsItemType[]>(`/api/news/${ticker}`, { params: { exchange } });
  return response.data;
}
