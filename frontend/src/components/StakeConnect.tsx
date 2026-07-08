import { useState } from 'react';
import clsx from 'clsx';
import { useSetStakeToken, useStakeLogin, useStakeStatus } from '../hooks/useHoldings';
import { errorMessage } from '../utils/errors';

function tokenAge(savedAt?: string | null) {
  if (!savedAt) return null;
  const saved = new Date(savedAt);
  if (Number.isNaN(saved.getTime())) return null;
  const days = Math.max(0, Math.floor((Date.now() - saved.getTime()) / 86_400_000));
  return days === 0 ? 'saved today' : `saved ${days} day${days === 1 ? '' : 's'} ago`;
}

export default function StakeConnect() {
  const status = useStakeStatus();
  const tokenMutation = useSetStakeToken();
  const loginMutation = useStakeLogin();
  const [token, setToken] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [otp, setOtp] = useState('');

  const connected = status.data?.configured ?? false;
  const lastSync = status.data?.last_sync;
  const tokenState = status.data?.token_state ?? 'none';
  const age = tokenAge(status.data?.token_saved_at);
  const statusCopy = {
    none: connected ? 'Stake connected' : 'Stake not connected',
    ok: 'Stake connected',
    expiring_soon: 'Token expires soon - re-connect',
    expired: 'Token expired - re-connect',
  }[tokenState];
  const dotClass = {
    none: connected ? 'bg-emerald-400' : 'bg-slate-500',
    ok: 'bg-emerald-400',
    expiring_soon: 'bg-amber-400',
    expired: 'bg-red-400',
  }[tokenState];

  const clearLoginFields = () => {
    setUsername('');
    setPassword('');
    setOtp('');
  };

  const handleLoginSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!username.trim() || !password) return;
    loginMutation.mutate(
      { username: username.trim(), password, otp: otp.trim() || undefined },
      { onSettled: clearLoginFields },
    );
  };

  const handleTokenSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    const trimmed = token.trim();
    if (!trimmed) return;
    tokenMutation.mutate(trimmed, { onSuccess: () => setToken('') });
  };

  return (
    <div className="space-y-4 text-sm text-slate-300">
      <div className="flex items-center gap-2">
        <span className={clsx('h-2.5 w-2.5 rounded-full', dotClass)} />
        <span className="font-medium text-slate-200">
          {statusCopy}
        </span>
        {connected && lastSync ? (
          <span className="text-xs text-slate-500">
            Last sync {new Date(lastSync).toLocaleString('en-AU')}
          </span>
        ) : null}
        {age ? <span className="text-xs text-slate-500">{age}</span> : null}
      </div>

      <form onSubmit={handleLoginSubmit} className="space-y-3 rounded border border-slate-800 bg-slate-950/40 p-3">
        <div className="grid gap-3 sm:grid-cols-2">
          <label htmlFor="stake-username" className="block text-xs text-slate-400">
            Username
            <input
              id="stake-username"
              type="text"
              autoComplete="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              className="mt-1 w-full rounded bg-slate-800 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-sky-500"
            />
          </label>
          <label htmlFor="stake-password" className="block text-xs text-slate-400">
            Password
            <input
              id="stake-password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="mt-1 w-full rounded bg-slate-800 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-sky-500"
            />
          </label>
        </div>
        <label htmlFor="stake-otp" className="block text-xs text-slate-400">
          2FA code - required if your account has 2FA enabled
          <input
            id="stake-otp"
            type="text"
            inputMode="numeric"
            autoComplete="one-time-code"
            value={otp}
            onChange={(event) => setOtp(event.target.value)}
            className="mt-1 w-full rounded bg-slate-800 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-sky-500"
          />
        </label>
        <button
          type="submit"
          disabled={loginMutation.isPending || !username.trim() || !password}
          className="rounded bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-500 disabled:cursor-not-allowed disabled:bg-slate-700"
        >
          {loginMutation.isPending ? 'Connecting...' : connected ? 'Re-connect' : 'Connect'}
        </button>
        {loginMutation.isSuccess ? <p className="text-xs text-emerald-400">Stake connected.</p> : null}
        {loginMutation.error ? <p className="text-xs text-red-300">{errorMessage(loginMutation.error)}</p> : null}
      </form>

      <details className="rounded border border-slate-800 bg-slate-950/40 p-3 text-xs text-slate-400">
        <summary className="cursor-pointer text-slate-300">Or paste a session token manually</summary>
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
        <form onSubmit={handleTokenSubmit} className="mt-3 space-y-2">
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
            disabled={tokenMutation.isPending || !token.trim()}
            className="rounded bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-500 disabled:cursor-not-allowed disabled:bg-slate-700"
          >
            {tokenMutation.isPending ? 'Validating...' : connected ? 'Update token' : 'Connect'}
          </button>
          {tokenMutation.isSuccess ? <p className="text-xs text-emerald-400">Token saved and validated.</p> : null}
          {tokenMutation.error ? <p className="text-xs text-red-300">{errorMessage(tokenMutation.error)}</p> : null}
        </form>
      </details>
    </div>
  );
}
