import clsx from 'clsx';
import { useMemo, useState } from 'react';
import FeedCard from '../components/FeedCard';
import MarketStatusBadge from '../components/MarketStatusBadge';
import SettingsPanel from '../components/SettingsPanel';
import { useHoldings, useSyncStake, useUsage, useWatchlist } from '../hooks/useHoldings';
import type { Exchange, FeedAsset, MarketTab } from '../types';

const marketTabs: { label: string; value: MarketTab }[] = [
  { label: 'ASX', value: 'ASX' },
  { label: 'S&P / US', value: 'NYSE' },
  { label: 'All', value: 'ALL' },
];

const kindTabs = ['Holdings', 'Watchlist', 'All'] as const;
type KindTab = (typeof kindTabs)[number];

export default function Dashboard() {
  const [market, setMarket] = useState<MarketTab>('ALL');
  const [kind, setKind] = useState<KindTab>('All');
  const exchange = market === 'ALL' ? undefined : (market as Exchange);
  const holdings = useHoldings(exchange);
  const watchlist = useWatchlist(exchange);
  const usage = useUsage();
  const sync = useSyncStake();

  const assets = useMemo<FeedAsset[]>(() => {
    const holdingAssets = (holdings.data ?? []).map((item) => ({
      ticker: item.ticker,
      exchange: item.exchange,
      kind: 'holding' as const,
      quantity: item.quantity,
      avg_cost: item.avg_cost,
    }));
    const holdingKeys = new Set(holdingAssets.map((item) => `${item.ticker}:${item.exchange}`));
    const watchlistAssets = (watchlist.data ?? [])
      .filter((item) => !holdingKeys.has(`${item.ticker}:${item.exchange}`))
      .map((item) => ({ ticker: item.ticker, exchange: item.exchange, kind: 'watchlist' as const }));
    if (kind === 'Holdings') return holdingAssets;
    if (kind === 'Watchlist') return watchlistAssets;
    return [...holdingAssets, ...watchlistAssets].sort((a, b) => a.ticker.localeCompare(b.ticker));
  }, [holdings.data, kind, watchlist.data]);

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <header className="flex flex-col gap-4 border-b border-slate-800 pb-5 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-normal text-white">Stake Dashboard</h1>
            <div className="mt-2 flex flex-wrap gap-2">
              <MarketStatusBadge exchange="ASX" />
              <MarketStatusBadge exchange="NYSE" />
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <SettingsPanel />
            <span className="rounded border border-slate-700 px-3 py-2 text-sm text-slate-300">
              API Usage: {usage.data?.fmp?.today ?? 0}
            </span>
            <button
              type="button"
              onClick={() => sync.mutate()}
              disabled={sync.isPending}
              className="rounded bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-500 disabled:cursor-not-allowed disabled:bg-slate-700"
            >
              {sync.isPending ? 'Syncing' : 'Sync'}
            </button>
          </div>
        </header>

        <section className="mt-5 space-y-4">
          <div className="flex flex-wrap gap-2">
            {marketTabs.map((tab) => (
              <button
                key={tab.value}
                type="button"
                onClick={() => setMarket(tab.value)}
                className={clsx(
                  'rounded px-3 py-2 text-sm font-semibold',
                  market === tab.value ? 'bg-slate-100 text-slate-950' : 'bg-slate-800 text-slate-300 hover:bg-slate-700',
                )}
              >
                {tab.label}
              </button>
            ))}
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap gap-2">
              {kindTabs.map((tab) => (
                <button
                  key={tab}
                  type="button"
                  onClick={() => setKind(tab)}
                  className={clsx(
                    'rounded px-3 py-2 text-sm',
                    kind === tab ? 'bg-sky-500/20 text-sky-200' : 'bg-slate-800 text-slate-400 hover:bg-slate-700',
                  )}
                >
                  {tab}
                </button>
              ))}
            </div>
            <span className="text-sm text-slate-500">Market status: ASX / NYSE</span>
          </div>
        </section>

        <section className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {assets.map((asset) => (
            <FeedCard key={`${asset.ticker}:${asset.exchange}:${asset.kind}`} asset={asset} />
          ))}
        </section>

        {!assets.length ? (
          <div className="mt-10 rounded-lg border border-dashed border-slate-700 p-8 text-center text-slate-400">
            No holdings or watchlist entries available.
          </div>
        ) : null}

        {(holdings.isError || watchlist.isError) && (
          <div className="mt-6 rounded border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
            Unable to load portfolio data from the backend.
          </div>
        )}
      </div>
    </main>
  );
}
