import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { fetchHoldings, fetchUsage, fetchWatchlist, syncStake } from '../api/holdings';
import type { Exchange } from '../types';

export function useHoldings(exchange?: Exchange) {
  return useQuery({ queryKey: ['holdings', exchange], queryFn: () => fetchHoldings(exchange) });
}

export function useWatchlist(exchange?: Exchange) {
  return useQuery({ queryKey: ['watchlist', exchange], queryFn: () => fetchWatchlist(exchange) });
}

export function useUsage() {
  return useQuery({ queryKey: ['usage'], queryFn: fetchUsage, refetchInterval: 300_000 });
}

export function useSyncStake() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: syncStake,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['holdings'] });
      queryClient.invalidateQueries({ queryKey: ['watchlist'] });
    },
  });
}
