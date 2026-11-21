import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Suspense, lazy } from 'react';
import { Link, Route, Routes } from 'react-router-dom';

import { useWatchlist } from './lib/watchlist';
import { ScreenerPage } from './pages/ScreenerPage';
import { WatchlistPage } from './pages/WatchlistPage';

const CompanyPage = lazy(async () => {
  const module = await import('./pages/CompanyPage');
  return { default: module.CompanyPage };
});

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1 } },
});

export default function App() {
  const watchlist = useWatchlist();

  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen bg-slate-50 text-slate-900">
        <header className="border-b border-slate-200 bg-white">
          <div className="mx-auto flex max-w-[1600px] items-center gap-3 px-5 py-3">
            <Link to="/" className="text-lg font-semibold tracking-tight">
              Stockscope
            </Link>
            <span className="text-xs text-slate-500">Public company screener</span>
            <Link to="/watchlist" className="ml-auto text-sm text-sky-700 hover:underline">
              Watchlist ({watchlist.tickers.length})
            </Link>
          </div>
        </header>
        <main className="mx-auto max-w-[1600px] px-5 py-5">
          <Routes>
            <Route path="/" element={<ScreenerPage watchlist={watchlist} />} />
            <Route
              path="/watchlist"
              element={<WatchlistPage tickers={watchlist.tickers} onRemove={watchlist.remove} />}
            />
            <Route
              path="/companies/:ticker"
              element={
                <Suspense fallback={<p className="text-sm">Loading company…</p>}>
                  <CompanyPage />
                </Suspense>
              }
            />
          </Routes>
        </main>
      </div>
    </QueryClientProvider>
  );
}
