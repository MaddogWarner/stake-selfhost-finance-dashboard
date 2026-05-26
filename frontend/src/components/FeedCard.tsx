import clsx from 'clsx';
import { useFundamentals } from '../hooks/useFundamentals';
import { useNews } from '../hooks/useNews';
import { usePrices } from '../hooks/usePrices';
import type { FeedAsset } from '../types';
import NewsItem from './NewsItem';
import PriceChart from './PriceChart';
import SignalBadge from './SignalBadge';

function formatMoney(value: number | null | undefined, currency: string | null | undefined) {
  if (value === null || value === undefined) return '-';
  return new Intl.NumberFormat('en-AU', { style: 'currency', currency: currency || 'AUD', maximumFractionDigits: 2 }).format(value);
}

function formatMarketCap(value: number | null | undefined) {
  if (!value) return '-';
  if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(1)}B`;
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  return value.toLocaleString('en-AU');
}

export default function FeedCard({ asset }: { asset: FeedAsset }) {
  const price = usePrices(asset.ticker, asset.exchange);
  const fundamentals = useFundamentals(asset.ticker, asset.exchange);
  const news = useNews(asset.ticker, asset.exchange);

  const quote = price.data;
  const profile = fundamentals.data;
  const change = quote?.day_change ?? 0;
  const changePositive = change >= 0;
  const history = quote?.history ?? [];
  const closes = history.map((point) => point.close).filter((value): value is number => typeof value === 'number');
  const week52High = quote?.week52_high ?? null;
  const week52Low = quote?.week52_low ?? null;
  const movingAverage50 = quote?.moving_average_50 ?? null;
  const latest = quote?.price ?? closes[closes.length - 1] ?? null;

  return (
    <article className="rounded-lg border border-slate-700 bg-slate-900 p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-white">{asset.ticker}</h2>
            <span
              className={clsx(
                'rounded px-2 py-1 text-xs font-semibold',
                asset.exchange === 'ASX' ? 'bg-emerald-500/15 text-emerald-300' : 'bg-sky-500/15 text-sky-300',
              )}
            >
              {asset.exchange}
            </span>
          </div>
          <p className="mt-1 line-clamp-1 text-sm text-slate-400">{profile?.name ?? 'Company profile pending'}</p>
        </div>
        <span className="rounded bg-slate-800 px-2 py-1 text-xs text-slate-300">
          {asset.kind === 'holding' ? 'Holding' : 'Watchlist'}
        </span>
      </div>

      <div className="mt-4 flex items-end justify-between gap-3">
        <div>
          <div className="text-3xl font-semibold text-white">{formatMoney(latest, quote?.currency)}</div>
          <div className={clsx('text-sm', changePositive ? 'text-emerald-300' : 'text-red-300')}>
            {formatMoney(quote?.day_change, quote?.currency)} {quote?.day_change_pct?.toFixed(2) ?? '-'}%
          </div>
        </div>
        {profile?.sector ? <span className="rounded bg-slate-800 px-2 py-1 text-xs text-slate-300">{profile.sector}</span> : null}
      </div>

      <div className="mt-4">
        <PriceChart data={history} />
      </div>

      <div className="mt-4 grid grid-cols-3 gap-2 text-sm">
        <div className="rounded bg-slate-800 p-2">
          <div className="text-xs text-slate-500">P/E</div>
          <div className="font-semibold text-slate-100">{profile?.pe_ratio ?? '-'}</div>
        </div>
        <div className="rounded bg-slate-800 p-2">
          <div className="text-xs text-slate-500">Market Cap</div>
          <div className="font-semibold text-slate-100">{formatMarketCap(profile?.market_cap)}</div>
        </div>
        <div className="rounded bg-slate-800 p-2">
          <div className="text-xs text-slate-500">Range</div>
          <div className="font-semibold text-slate-100">
            {week52Low && week52High ? `${week52Low.toFixed(2)}-${week52High.toFixed(2)}` : '-'}
          </div>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {latest && week52High && latest >= week52High * 0.98 ? <SignalBadge label="Near 52W High" tone="good" /> : null}
        {latest && week52Low && latest <= week52Low * 1.02 ? <SignalBadge label="Near 52W Low" tone="bad" /> : null}
        {latest && movingAverage50 ? (
          latest >= movingAverage50 ? (
            <SignalBadge label="Above 50MA" tone="good" />
          ) : (
            <SignalBadge label="Below 50MA" tone="bad" />
          )
        ) : null}
      </div>

      <div className="mt-4 space-y-2">
        {(news.data ?? []).slice(0, 2).map((item) => (
          <NewsItem key={`${item.url ?? item.headline}`} item={item} />
        ))}
        {news.isError ? <p className="text-sm text-slate-500">News unavailable.</p> : null}
      </div>

      <div className="mt-4 border-t border-slate-800 pt-3 text-sm text-slate-400">
        {asset.kind === 'holding'
          ? `Holding: ${asset.quantity} shares @ ${asset.avg_cost ?? '-'} avg`
          : 'Watchlist'}
      </div>
    </article>
  );
}
