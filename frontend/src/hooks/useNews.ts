import { useQuery } from '@tanstack/react-query';
import { fetchNews } from '../api/news';
import type { Exchange } from '../types';

export function useNews(ticker: string, exchange: Exchange) {
  return useQuery({
    queryKey: ['news', ticker, exchange],
    queryFn: () => fetchNews(ticker, exchange),
    staleTime: 300_000,
  });
}
