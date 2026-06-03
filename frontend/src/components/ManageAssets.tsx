import { useState } from 'react';
import {
  useAddWatchlist,
  useCreateHolding,
  useDeleteHolding,
  useHoldings,
  useRemoveWatchlist,
  useUpdateHolding,
  useWatchlist,
} from '../hooks/useHoldings';
import type { Exchange } from '../types';
import { errorMessage } from '../utils/errors';

const EXCHANGES: Exchange[] = ['ASX', 'NYSE'];

const inputClass =
  'rounded bg-slate-800 px-2 py-1 text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-sky-500 disabled:opacity-50';
const sourceBadge = (source: string) =>
  source === 'stake'
    ? 'rounded bg-sky-500/15 px-2 py-0.5 text-xs text-sky-300'
    : 'rounded bg-slate-700 px-2 py-0.5 text-xs text-slate-300';

export default function ManageAssets() {
  const holdings = useHoldings();
  const watchlist = useWatchlist();
  const createHolding = useCreateHolding();
  const updateHolding = useUpdateHolding();
  const deleteHolding = useDeleteHolding();
  const addWatchlist = useAddWatchlist();
  const removeWatchlist = useRemoveWatchlist();

  const [editingId, setEditingId] = useState<number | null>(null);
  const [hTicker, setHTicker] = useState('');
  const [hExchange, setHExchange] = useState<Exchange>('ASX');
  const [hQty, setHQty] = useState('');
  const [hAvg, setHAvg] = useState('');

  const [wTicker, setWTicker] = useState('');
  const [wExchange, setWExchange] = useState<Exchange>('ASX');

  const resetHoldingForm = () => {
    setEditingId(null);
    setHTicker('');
    setHQty('');
    setHAvg('');
  };

  const submitHolding = (event: React.FormEvent) => {
    event.preventDefault();
    if (editingId !== null) {
      updateHolding.mutate(
        { id: editingId, payload: { quantity: hQty, avg_cost: hAvg || null } },
        { onSuccess: resetHoldingForm },
      );
      return;
    }
    if (!hTicker.trim() || !hQty) return;
    createHolding.mutate(
      { ticker: hTicker.trim(), exchange: hExchange, quantity: hQty, avg_cost: hAvg || null },
      { onSuccess: resetHoldingForm },
    );
  };

  const submitWatchlist = (event: React.FormEvent) => {
    event.preventDefault();
    if (!wTicker.trim()) return;
    addWatchlist.mutate(
      { ticker: wTicker.trim(), exchange: wExchange },
      { onSuccess: () => setWTicker('') },
    );
  };

  const startEdit = (id: number, ticker: string, exchange: Exchange, qty: string, avg: string | null) => {
    setEditingId(id);
    setHTicker(ticker);
    setHExchange(exchange);
    setHQty(qty);
    setHAvg(avg ?? '');
  };

  const holdingError = createHolding.error || updateHolding.error || deleteHolding.error;
  const watchlistError = addWatchlist.error || removeWatchlist.error;

  return (
    <div className="space-y-8">
      {/* Holdings */}
      <section className="space-y-3">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">Holdings</h3>
        <form onSubmit={submitHolding} className="flex flex-wrap items-end gap-2">
          <input
            aria-label="Holding ticker"
            value={hTicker}
            onChange={(event) => setHTicker(event.target.value)}
            placeholder="Ticker"
            disabled={editingId !== null}
            className={`${inputClass} w-24`}
          />
          <select
            aria-label="Holding exchange"
            value={hExchange}
            onChange={(event) => setHExchange(event.target.value as Exchange)}
            disabled={editingId !== null}
            className={inputClass}
          >
            {EXCHANGES.map((ex) => (
              <option key={ex} value={ex}>
                {ex}
              </option>
            ))}
          </select>
          <input
            aria-label="Quantity"
            type="number"
            step="any"
            min="0"
            value={hQty}
            onChange={(event) => setHQty(event.target.value)}
            placeholder="Quantity"
            className={`${inputClass} w-28`}
          />
          <input
            aria-label="Average cost"
            type="number"
            step="any"
            min="0"
            value={hAvg}
            onChange={(event) => setHAvg(event.target.value)}
            placeholder="Avg cost"
            className={`${inputClass} w-28`}
          />
          <button
            type="submit"
            disabled={createHolding.isPending || updateHolding.isPending}
            className="rounded bg-sky-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-sky-500 disabled:bg-slate-700"
          >
            {editingId !== null ? 'Save' : 'Add'}
          </button>
          {editingId !== null ? (
            <button type="button" onClick={resetHoldingForm} className="px-2 py-1.5 text-sm text-slate-400 hover:text-white">
              Cancel
            </button>
          ) : null}
        </form>
        {holdingError ? <p className="text-xs text-red-300">{errorMessage(holdingError)}</p> : null}
        <ul className="divide-y divide-slate-800 rounded border border-slate-800">
          {(holdings.data ?? []).map((h) => (
            <li key={h.id} className="flex items-center justify-between gap-2 px-3 py-2 text-sm">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-slate-100">{h.ticker}</span>
                <span className="text-xs text-slate-500">{h.exchange}</span>
                <span className={sourceBadge(h.source)}>{h.source === 'stake' ? 'Stake' : 'Manual'}</span>
              </div>
              <div className="flex items-center gap-3 text-slate-400">
                <span>
                  {h.quantity} @ {h.avg_cost ?? '-'}
                </span>
                <button
                  type="button"
                  onClick={() => startEdit(h.id, h.ticker, h.exchange, h.quantity, h.avg_cost)}
                  className="text-sky-300 hover:text-sky-200"
                >
                  Edit
                </button>
                <button
                  type="button"
                  onClick={() => deleteHolding.mutate(h.id)}
                  className="text-red-300 hover:text-red-200"
                >
                  Delete
                </button>
              </div>
            </li>
          ))}
          {!(holdings.data ?? []).length ? (
            <li className="px-3 py-2 text-sm text-slate-500">No holdings yet.</li>
          ) : null}
        </ul>
      </section>

      {/* Watchlist */}
      <section className="space-y-3">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">Watchlist</h3>
        <form onSubmit={submitWatchlist} className="flex flex-wrap items-end gap-2">
          <input
            aria-label="Watchlist ticker"
            value={wTicker}
            onChange={(event) => setWTicker(event.target.value)}
            placeholder="Ticker"
            className={`${inputClass} w-24`}
          />
          <select
            aria-label="Watchlist exchange"
            value={wExchange}
            onChange={(event) => setWExchange(event.target.value as Exchange)}
            className={inputClass}
          >
            {EXCHANGES.map((ex) => (
              <option key={ex} value={ex}>
                {ex}
              </option>
            ))}
          </select>
          <button
            type="submit"
            disabled={addWatchlist.isPending}
            className="rounded bg-sky-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-sky-500 disabled:bg-slate-700"
          >
            Add
          </button>
        </form>
        {watchlistError ? <p className="text-xs text-red-300">{errorMessage(watchlistError)}</p> : null}
        <ul className="divide-y divide-slate-800 rounded border border-slate-800">
          {(watchlist.data ?? []).map((w) => (
            <li key={w.id} className="flex items-center justify-between gap-2 px-3 py-2 text-sm">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-slate-100">{w.ticker}</span>
                <span className="text-xs text-slate-500">{w.exchange}</span>
                <span className={sourceBadge(w.source)}>{w.source === 'stake' ? 'Stake' : 'Manual'}</span>
              </div>
              <button
                type="button"
                onClick={() => removeWatchlist.mutate(w.id)}
                className="text-red-300 hover:text-red-200"
              >
                Delete
              </button>
            </li>
          ))}
          {!(watchlist.data ?? []).length ? (
            <li className="px-3 py-2 text-sm text-slate-500">No watchlist entries yet.</li>
          ) : null}
        </ul>
      </section>
    </div>
  );
}
