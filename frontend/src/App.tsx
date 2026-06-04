import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Dashboard from './pages/Dashboard';
import { RefreshProvider } from './hooks/useRefresh';

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
      <RefreshProvider>
        <Dashboard />
      </RefreshProvider>
    </QueryClientProvider>
  );
}
