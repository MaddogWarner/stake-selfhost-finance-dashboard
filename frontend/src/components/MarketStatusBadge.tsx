import clsx from 'clsx';
import type { Exchange } from '../types';

function isMarketOpen(exchange: Exchange): boolean {
  const timezone = exchange === 'ASX' ? 'Australia/Sydney' : 'America/New_York';
  const parts = new Intl.DateTimeFormat('en-AU', {
    timeZone: timezone,
    hour: 'numeric',
    minute: 'numeric',
    weekday: 'short',
    hour12: false,
  }).formatToParts(new Date());
  const get = (type: string) => parts.find((part) => part.type === type)?.value ?? '';
  const weekday = get('weekday');
  const totalMinutes = parseInt(get('hour'), 10) * 60 + parseInt(get('minute'), 10);

  if (['Sat', 'Sun'].includes(weekday) || Number.isNaN(totalMinutes)) return false;
  return exchange === 'ASX' ? totalMinutes >= 600 && totalMinutes <= 960 : totalMinutes >= 570 && totalMinutes <= 960;
}

export default function MarketStatusBadge({ exchange }: { exchange: Exchange }) {
  const open = isMarketOpen(exchange);
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded px-2 py-1 text-xs font-semibold',
        open ? 'bg-emerald-500/15 text-emerald-300' : 'bg-slate-700 text-slate-300',
      )}
    >
      {exchange} {open ? 'OPEN' : 'CLOSED'}
    </span>
  );
}
