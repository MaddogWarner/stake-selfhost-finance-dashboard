import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { fetchStakeStatus, fetchUsage, setStakeToken, stakeLogin } from '../api/admin';
import {
  addWatchlist,
  createHolding,
  deleteHolding,
  fetchHoldings,
  fetchWatchlist,
  removeWatchlist,
  syncStake,
  updateHolding,
} from '../api/holdings';
import type { Exchange, HoldingUpdate } from '../types';

export function useHoldings(exchange?: Exchange) {
  return useQuery({ queryKey: ['holdings', exchange], queryFn: () => fetchHoldings(exchange) });
}

export function useWatchlist(exchange?: Exchange) {
  return useQuery({ queryKey: ['watchlist', exchange], queryFn: () => fetchWatchlist(exchange) });
}

export function useUsage() {
  return useQuery({ queryKey: ['usage'], queryFn: fetchUsage, refetchInterval: 300_000 });
}

function useInvalidateAssets() {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ['holdings'] });
    queryClient.invalidateQueries({ queryKey: ['watchlist'] });
  };
}

export function useSyncStake() {
  const invalidate = useInvalidateAssets();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: syncStake,
    onSuccess: () => {
      invalidate();
      queryClient.invalidateQueries({ queryKey: ['stake-status'] });
    },
  });
}

export function useCreateHolding() {
  const invalidate = useInvalidateAssets();
  return useMutation({ mutationFn: createHolding, onSuccess: invalidate });
}

export function useUpdateHolding() {
  const invalidate = useInvalidateAssets();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: HoldingUpdate }) => updateHolding(id, payload),
    onSuccess: invalidate,
  });
}

export function useDeleteHolding() {
  const invalidate = useInvalidateAssets();
  return useMutation({ mutationFn: deleteHolding, onSuccess: invalidate });
}

export function useAddWatchlist() {
  const invalidate = useInvalidateAssets();
  return useMutation({ mutationFn: addWatchlist, onSuccess: invalidate });
}

export function useRemoveWatchlist() {
  const invalidate = useInvalidateAssets();
  return useMutation({ mutationFn: removeWatchlist, onSuccess: invalidate });
}

export function useStakeStatus() {
  return useQuery({ queryKey: ['stake-status'], queryFn: fetchStakeStatus });
}

export function useSetStakeToken() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: setStakeToken,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['stake-status'] }),
  });
}

export function useStakeLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: stakeLogin,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['stake-status'] }),
  });
}
