import { useQuery } from '@tanstack/react-query';
import { fetchPrice } from '../api/prices';
import { useRefreshInterval } from './useRefresh';
import type { Exchange } from '../types';

export function usePrices(ticker: string, exchange: Exchange) {
  const { intervalMs } = useRefreshInterval();
  return useQuery({
    queryKey: ['price', ticker, exchange],
    queryFn: () => fetchPrice(ticker, exchange),
    refetchInterval: intervalMs,
  });
}
