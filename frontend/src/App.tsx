import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Suspense, lazy } from 'react';
import { Link, Route, Routes } from 'react-router-dom';

import { useAlerts } from './lib/alerts';
import { usePortfolio } from './lib/portfolio';
import { useWatchlist } from './lib/watchlist';
import { AlertsPage } from './pages/AlertsPage';
import { DividendsPage } from './pages/DividendsPage';
import { HeatmapPage } from './pages/HeatmapPage';
import { PortfolioPage } from './pages/PortfolioPage';
import { ScreenerPage } from './pages/ScreenerPage';
import { WatchlistPage } from './pages/WatchlistPage';

const CompanyPage = lazy(async () => {
  const module = await import('./pages/CompanyPage');
  return { default: module.CompanyPage };
});

const SimulatorPage = lazy(async () => {
  const module = await import('./pages/SimulatorPage');
  return { default: module.SimulatorPage };
});

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1 } },
});

export default function App() {
  const watchlist = useWatchlist();
  const portfolio = usePortfolio();
  const alerts = useAlerts();

  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen bg-slate-50 text-slate-900">
        <header className="border-b border-slate-200 bg-white">
          <div className="mx-auto flex max-w-[1600px] items-center gap-3 px-5 py-3">
            <Link to="/" className="text-lg font-semibold tracking-tight">
              Stockscope
            </Link>
            <span className="text-xs text-slate-500">Public company screener</span>
            <Link to="/alerts" className="ml-auto text-sm text-sky-700 hover:underline">
              Alerts ({alerts.alerts.length})
            </Link>
            <Link to="/heatmap" className="text-sm text-sky-700 hover:underline">
              Heatmap
            </Link>
            <Link to="/dividends" className="text-sm text-sky-700 hover:underline">
              Dividends
            </Link>
            <Link to="/simulator" className="text-sm text-sky-700 hover:underline">
              Simulator
            </Link>
            <Link to="/portfolio" className="text-sm text-sky-700 hover:underline">
              Portfolio ({portfolio.holdings.length})
            </Link>
            <Link to="/watchlist" className="text-sm text-sky-700 hover:underline">
              Watchlist ({watchlist.tickers.length})
            </Link>
          </div>
        </header>
        <main className="mx-auto max-w-[1600px] px-5 py-5">
          <Routes>
            <Route path="/" element={<ScreenerPage watchlist={watchlist} />} />
            <Route
              path="/simulator"
              element={
                <Suspense fallback={<p className="text-sm">Loading simulator…</p>}>
                  <SimulatorPage />
                </Suspense>
              }
            />
            <Route
              path="/watchlist"
              element={<WatchlistPage tickers={watchlist.tickers} onRemove={watchlist.remove} />}
            />
            <Route path="/heatmap" element={<HeatmapPage />} />
            <Route
              path="/alerts"
              element={
                <AlertsPage alerts={alerts.alerts} onAdd={alerts.add} onRemove={alerts.remove} />
              }
            />
            <Route
              path="/dividends"
              element={
                <DividendsPage
                  tickers={[
                    ...new Set([
                      ...watchlist.tickers,
                      ...portfolio.holdings.map((holding) => holding.ticker),
                    ]),
                  ]}
                />
              }
            />
            <Route
              path="/portfolio"
              element={
                <PortfolioPage
                  holdings={portfolio.holdings}
                  onAdd={portfolio.add}
                  onRemove={portfolio.remove}
                />
              }
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
