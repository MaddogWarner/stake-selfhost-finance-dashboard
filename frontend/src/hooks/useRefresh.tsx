import { createContext, useContext, useMemo, useState, type ReactNode } from 'react';

type RefreshInterval = number | false;

interface RefreshContextValue {
  intervalMs: RefreshInterval;
  setIntervalMs: (value: RefreshInterval) => void;
}

const RefreshContext = createContext<RefreshContextValue>({
  intervalMs: false,
  setIntervalMs: () => undefined,
});

// Default to 5 minutes, matching the price cache TTL on the backend.
export function RefreshProvider({ children }: { children: ReactNode }) {
  const [intervalMs, setIntervalMs] = useState<RefreshInterval>(300_000);
  const value = useMemo(() => ({ intervalMs, setIntervalMs }), [intervalMs]);
  return <RefreshContext.Provider value={value}>{children}</RefreshContext.Provider>;
}

export function useRefreshInterval() {
  return useContext(RefreshContext);
}
