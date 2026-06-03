import { useState } from 'react';
import { useSetStakeToken, useStakeStatus } from '../hooks/useHoldings';
import { errorMessage } from '../utils/errors';

export default function StakeConnect() {
  const status = useStakeStatus();
  const { mutate, isPending, isSuccess, error } = useSetStakeToken();
  const [token, setToken] = useState('');

  const connected = status.data?.configured ?? false;
  const lastSync = status.data?.last_sync;

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    const trimmed = token.trim();
    if (!trimmed) return;
    mutate(trimmed, { onSuccess: () => setToken('') });
  };

  return (
    <div className="space-y-4 text-sm text-slate-300">
      <div className="flex items-center gap-2">
        <span
          className={connected ? 'h-2.5 w-2.5 rounded-full bg-emerald-400' : 'h-2.5 w-2.5 rounded-full bg-slate-500'}
        />
        <span className="font-medium text-slate-200">
          {connected ? 'Stake connected' : 'Stake not connected'}
        </span>
        {connected && lastSync ? (
          <span className="text-xs text-slate-500">
            Last sync {new Date(lastSync).toLocaleString('en-AU')}
          </span>
        ) : null}
      </div>

      <details className="rounded border border-slate-800 bg-slate-950/40 p-3 text-xs text-slate-400">
        <summary className="cursor-pointer text-slate-300">How to get your session token</summary>
        <ol className="mt-2 list-decimal space-y-1 pl-4">
          <li>
            Log in at <span className="text-slate-200">trading.hellostake.com</span> in your browser.
          </li>
          <li>Open DevTools (F12) → <span className="text-slate-200">Network</span> tab, then click around the app.</li>
          <li>
            Click any request to <span className="text-slate-200">api2.prd.hellostake.com</span> and find the{' '}
            <span className="text-slate-200">Stake-Session-Token</span> request header.
          </li>
          <li>Copy its value and paste it below. Tokens last ~30 days.</li>
        </ol>
        <p className="mt-2">
          Stake sync is optional — your manually added holdings and watchlist work without it.
        </p>
      </details>

      <form onSubmit={handleSubmit} className="space-y-2">
        <label htmlFor="stake-token" className="block text-xs text-slate-400">
          Stake-Session-Token
        </label>
        <input
          id="stake-token"
          type="password"
          autoComplete="off"
          value={token}
          onChange={(event) => setToken(event.target.value)}
          placeholder="Paste token here"
          className="w-full rounded bg-slate-800 px-3 py-2 text-slate-100 focus:outline-none focus:ring-1 focus:ring-sky-500"
        />
        <button
          type="submit"
          disabled={isPending || !token.trim()}
          className="rounded bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-500 disabled:cursor-not-allowed disabled:bg-slate-700"
        >
          {isPending ? 'Validating…' : connected ? 'Update token' : 'Connect'}
        </button>
        {isSuccess ? <p className="text-xs text-emerald-400">Token saved and validated.</p> : null}
        {error ? <p className="text-xs text-red-300">{errorMessage(error)}</p> : null}
      </form>
    </div>
  );
}
