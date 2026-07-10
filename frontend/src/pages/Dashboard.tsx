import clsx from 'clsx';
import { useMemo, useState } from 'react';
import FeedCard from '../components/FeedCard';
import ManageAssets from '../components/ManageAssets';
import MarketStatusBadge from '../components/MarketStatusBadge';
import Modal from '../components/Modal';
import RefreshControls from '../components/RefreshControls';
import SettingsPanel from '../components/SettingsPanel';
import StakeConnect from '../components/StakeConnect';
import { useHoldings, useStakeStatus, useSyncStake, useUsage, useVersion, useWatchlist } from '../hooks/useHoldings';
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
  const [modal, setModal] = useState<'manage' | 'stake' | null>(null);
  const exchange = market === 'ALL' ? undefined : (market as Exchange);
  const holdings = useHoldings(exchange);
  const watchlist = useWatchlist(exchange);
  const usage = useUsage();
  const sync = useSyncStake();
  const stakeStatus = useStakeStatus();
  const version = useVersion();
  const [stakeBannerDismissed, setStakeBannerDismissed] = useState(false);
  const tokenState = stakeStatus.data?.token_state;
  const showStakeBanner = !stakeBannerDismissed && (tokenState === 'expired' || tokenState === 'expiring_soon');

  const assets = useMemo<FeedAsset[]>(() => {
    const holdingAssets = (holdings.data ?? []).map((item) => ({
      ticker: item.ticker,
      exchange: item.exchange,
      kind: 'holding' as const,
      quantity: item.quantity,
      avg_cost: item.avg_cost,
      source: item.source,
    }));
    const holdingKeys = new Set(holdingAssets.map((item) => `${item.ticker}:${item.exchange}`));
    const watchlistAssets = (watchlist.data ?? [])
      .filter((item) => !holdingKeys.has(`${item.ticker}:${item.exchange}`))
      .map((item) => ({ ticker: item.ticker, exchange: item.exchange, kind: 'watchlist' as const, source: item.source }));
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
            <RefreshControls />
            <span className="rounded border border-slate-700 px-3 py-2 text-sm text-slate-300">
              API Usage: {usage.data?.fmp?.today ?? 0}
            </span>
            <button
              type="button"
              onClick={() => setModal('manage')}
              className="rounded bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-white"
            >
              Manage
            </button>
            <button
              type="button"
              onClick={() => setModal('stake')}
              className="rounded border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-200 hover:bg-slate-800"
            >
              Connect Stake
            </button>
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

        {showStakeBanner ? (
          <div
            className={clsx(
              'mt-4 flex flex-col gap-3 rounded border px-4 py-3 text-sm sm:flex-row sm:items-center sm:justify-between',
              tokenState === 'expired'
                ? 'border-red-500/40 bg-red-500/10 text-red-100'
                : 'border-amber-500/40 bg-amber-500/10 text-amber-100',
            )}
          >
            <span>
              {tokenState === 'expired'
                ? 'Stake token expired - holdings are no longer syncing. Re-connect in Manage.'
                : 'Stake token expires soon - holdings may stop syncing. Re-connect in Manage.'}
            </span>
            <button
              type="button"
              onClick={() => setStakeBannerDismissed(true)}
              className="self-start rounded border border-current px-3 py-1 text-xs font-semibold text-current hover:bg-white/10 sm:self-auto"
            >
              Dismiss
            </button>
          </div>
        ) : null}

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
            Nothing tracked yet. Use <span className="font-semibold text-slate-200">Manage</span> to add holdings or
            watchlist tickers, or <span className="font-semibold text-slate-200">Connect Stake</span> to sync automatically.
          </div>
        ) : null}

        {(holdings.isError || watchlist.isError) && (
          <div className="mt-6 rounded border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
            Unable to load portfolio data from the backend.
          </div>
        )}

        <footer className="mt-10 border-t border-slate-800 pt-4 text-center text-xs text-slate-600">
          Stake Dashboard{version.data ? ` v${version.data}` : ''}
        </footer>
      </div>

      {modal === 'manage' ? (
        <Modal title="Manage assets" onClose={() => setModal(null)}>
          <ManageAssets />
        </Modal>
      ) : null}
      {modal === 'stake' ? (
        <Modal title="Connect Stake" onClose={() => setModal(null)}>
          <StakeConnect />
        </Modal>
      ) : null}
    </main>
  );
}
