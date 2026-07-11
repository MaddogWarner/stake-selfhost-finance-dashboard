import { useEffect, useState } from 'react';
import { fetchAuthStatus, login, setup, type AuthStatus } from '../api/auth';
import { errorMessage } from '../utils/errors';

function AuthCard({ mode, onAuthenticated }: { mode: 'setup' | 'login'; onAuthenticated: () => void }) {
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);
  const isSetup = mode === 'setup';

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (isSetup && password !== confirm) {
      setError('Passwords do not match.');
      return;
    }
    setPending(true);
    setError('');
    try {
      await (isSetup ? setup(password) : login(password));
      onAuthenticated();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setPending(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-4 text-slate-100">
      <form onSubmit={submit} className="w-full max-w-md space-y-5 rounded-xl border border-slate-800 bg-slate-900 p-6 shadow-2xl">
        <div>
          <h1 className="text-2xl font-semibold text-white">{isSetup ? 'Secure your dashboard' : 'Stake Dashboard'}</h1>
          <p className="mt-2 text-sm text-slate-400">
            {isSetup ? 'Choose the admin password used to protect your financial dashboard.' : 'Enter your admin password to continue.'}
          </p>
        </div>
        <label className="block text-sm text-slate-300">
          Password
          <input autoFocus type="password" autoComplete={isSetup ? 'new-password' : 'current-password'} minLength={isSetup ? 10 : undefined} required value={password} onChange={(event) => setPassword(event.target.value)} className="mt-2 w-full rounded bg-slate-800 px-3 py-2 text-white outline-none ring-sky-500 focus:ring-1" />
        </label>
        {isSetup ? (
          <label className="block text-sm text-slate-300">
            Confirm password
            <input type="password" autoComplete="new-password" minLength={10} required value={confirm} onChange={(event) => setConfirm(event.target.value)} className="mt-2 w-full rounded bg-slate-800 px-3 py-2 text-white outline-none ring-sky-500 focus:ring-1" />
          </label>
        ) : null}
        {error ? <p className="rounded bg-red-500/10 px-3 py-2 text-sm text-red-300">{error}</p> : null}
        <button disabled={pending} className="w-full rounded bg-sky-600 px-4 py-2 font-semibold text-white hover:bg-sky-500 disabled:bg-slate-700">
          {pending ? 'Please wait...' : isSetup ? 'Complete setup' : 'Log in'}
        </button>
      </form>
    </main>
  );
}

export default function AuthGate({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<AuthStatus | 'loading'>('loading');
  useEffect(() => {
    fetchAuthStatus().then(setStatus).catch(() => setStatus('unauthenticated'));
    const unauthenticated = () => setStatus('unauthenticated');
    window.addEventListener('stake-auth-required', unauthenticated);
    return () => window.removeEventListener('stake-auth-required', unauthenticated);
  }, []);
  if (status === 'loading') return <main className="min-h-screen bg-slate-950" />;
  if (status === 'setup_required') return <AuthCard mode="setup" onAuthenticated={() => setStatus('authenticated')} />;
  if (status === 'unauthenticated') return <AuthCard mode="login" onAuthenticated={() => setStatus('authenticated')} />;
  return <>{children}</>;
}
