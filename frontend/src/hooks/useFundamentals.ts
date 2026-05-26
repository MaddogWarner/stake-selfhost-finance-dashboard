import { useQuery } from '@tanstack/react-query';
import { fetchFundamentals } from '../api/fundamentals';
import type { Exchange } from '../types';

export function useFundamentals(ticker: string, exchange: Exchange) {
  return useQuery({
    queryKey: ['fundamentals', ticker, exchange],
    queryFn: () => fetchFundamentals(ticker, exchange),
  });
}
