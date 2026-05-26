import clsx from 'clsx';

export default function SignalBadge({ label, tone = 'neutral' }: { label: string; tone?: 'good' | 'bad' | 'neutral' }) {
  return (
    <span
      className={clsx(
        'rounded px-2 py-1 text-xs font-medium',
        tone === 'good' && 'bg-emerald-500/10 text-emerald-300',
        tone === 'bad' && 'bg-red-500/10 text-red-300',
        tone === 'neutral' && 'bg-slate-700 text-slate-300',
      )}
    >
      {label}
    </span>
  );
}
