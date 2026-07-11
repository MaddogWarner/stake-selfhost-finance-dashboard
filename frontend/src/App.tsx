import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Dashboard from './pages/Dashboard';
import { RefreshProvider } from './hooks/useRefresh';
import AuthGate from './components/AuthGate';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 60_000,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthGate>
        <RefreshProvider>
          <Dashboard />
        </RefreshProvider>
      </AuthGate>
    </QueryClientProvider>
  );
}
