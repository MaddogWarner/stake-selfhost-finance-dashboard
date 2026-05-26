import { useQuery } from '@tanstack/react-query';
import { fetchPrice } from '../api/prices';
import type { Exchange } from '../types';

export function usePrices(ticker: string, exchange: Exchange) {
  return useQuery({
    queryKey: ['price', ticker, exchange],
    queryFn: () => fetchPrice(ticker, exchange),
    refetchInterval: 300_000,
  });
}
