import { useSettings, useUpdateSettings } from '../hooks/useSettings';
import type { DataSource } from '../types';

const SOURCE_LABELS: Record<DataSource, string> = {
  both: 'FMP + Yahoo Finance',
  yfinance: 'Yahoo Finance Only',
  fmp: 'FMP Only',
};

export default function SettingsPanel() {
  const { data: settings } = useSettings();
  const { mutate, isPending, isSuccess } = useUpdateSettings();

  return (
    <div className="flex items-center gap-2 text-sm text-slate-400">
      <label htmlFor="data-source" className="whitespace-nowrap">
        Data source
      </label>
      <select
        id="data-source"
        value={settings?.data_source ?? 'both'}
        disabled={isPending}
        onChange={(event) => mutate({ data_source: event.target.value as DataSource })}
        className="rounded bg-slate-800 px-2 py-1 text-xs text-slate-200 focus:outline-none"
      >
        {(Object.entries(SOURCE_LABELS) as [DataSource, string][]).map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </select>
      {isSuccess ? <span className="text-xs text-emerald-400">Saved</span> : null}
    </div>
  );
}
