import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Suspense, lazy } from 'react';
import { Link, Route, Routes } from 'react-router-dom';

import { ScreenerPage } from './pages/ScreenerPage';

const CompanyPage = lazy(async () => {
  const module = await import('./pages/CompanyPage');
  return { default: module.CompanyPage };
});

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 60_000, retry: 1 } },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen bg-slate-50 text-slate-900">
        <header className="border-b border-slate-200 bg-white">
          <div className="mx-auto flex max-w-[1600px] items-center gap-3 px-5 py-3">
            <Link to="/" className="text-lg font-semibold tracking-tight">
              Stockscope
            </Link>
            <span className="text-xs text-slate-500">Public company screener</span>
          </div>
        </header>
        <main className="mx-auto max-w-[1600px] px-5 py-5">
          <Routes>
            <Route path="/" element={<ScreenerPage />} />
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
