import { useIsFetching, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';
import { useRefreshInterval } from '../hooks/useRefresh';

const OPTIONS: { label: string; value: number | false }[] = [
  { label: 'Off', value: false },
  { label: '1 min', value: 60_000 },
  { label: '2 min', value: 120_000 },
  { label: '5 min', value: 300_000 },
];

export default function RefreshControls() {
  const { intervalMs, setIntervalMs } = useRefreshInterval();
  const queryClient = useQueryClient();
  const refreshing = useIsFetching({ queryKey: ['price'] }) > 0;
  const [confirmed, setConfirmed] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => () => clearTimeout(timeoutRef.current), []);

  const handleRefresh = async () => {
    clearTimeout(timeoutRef.current);
    setConfirmed(false);
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['price'] }),
      queryClient.invalidateQueries({ queryKey: ['news'] }),
    ]);
    setConfirmed(true);
    timeoutRef.current = setTimeout(() => setConfirmed(false), 3000);
  };

  return (
    <div className="flex items-center gap-2 text-sm text-slate-400">
      <label htmlFor="auto-refresh" className="whitespace-nowrap">
        Auto-refresh
      </label>
      <select
        id="auto-refresh"
        value={intervalMs === false ? 'off' : String(intervalMs)}
        onChange={(event) => setIntervalMs(event.target.value === 'off' ? false : Number(event.target.value))}
        className="rounded bg-slate-800 px-2 py-1 text-xs text-slate-200 focus:outline-none"
      >
        {OPTIONS.map((option) => (
          <option key={option.label} value={option.value === false ? 'off' : String(option.value)}>
            {option.label}
          </option>
        ))}
      </select>
      <button
        type="button"
        onClick={handleRefresh}
        disabled={refreshing}
        className="rounded border border-slate-700 px-3 py-2 text-sm font-semibold text-slate-200 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {refreshing ? 'Refreshing' : 'Refresh'}
      </button>
      {confirmed ? (
        <span className="rounded bg-emerald-500/15 px-2 py-1 text-xs font-semibold text-emerald-300">
          Refresh successful
        </span>
      ) : null}
    </div>
  );
}
