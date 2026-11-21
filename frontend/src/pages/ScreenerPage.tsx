import { useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useNavigate } from 'react-router-dom';

import { FilterBar } from '../components/FilterBar';
import { MetricsTable } from '../components/MetricsTable';
import { RankingPanel } from '../components/RankingPanel';
import { apiPost, exportScreen } from '../lib/api';
import {
  useDataQuality,
  useMetrics,
  useSavedScreen,
  useScreen,
  useSectors,
} from '../lib/queries';
import { savedScreenSchema } from '../lib/schemas';
import { defaultState, readState, stateToRequest, writeState, type ScreenState } from '../lib/state';

export function ScreenerPage() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const encodedState = params.get('s');
  const savedToken = encodedState === null ? params.get('screen') : null;
  const savedQuery = useSavedScreen(savedToken);
  const state = useMemo(
    () => (encodedState !== null ? readState(encodedState) : (savedQuery.data ?? defaultState)),
    [encodedState, savedQuery.data],
  );
  const metricsQuery = useMetrics();
  const metrics = useMemo(() => metricsQuery.data ?? [], [metricsQuery.data]);
  const request = useMemo(
    () => stateToRequest(state, metrics.map((metric) => metric.key)),
    [state, metrics],
  );
  const sectorsQuery = useSectors();
  const qualityQuery = useDataQuality();
  const screenQuery = useScreen(request);

  function update(next: ScreenState) {
    setParams(new URLSearchParams({ s: writeState(next) }), { replace: true });
  }

  async function saveScreen() {
    const saved = await apiPost('/api/v1/screens', savedScreenSchema, state);
    setParams(new URLSearchParams({ screen: saved.token }), { replace: true });
  }

  async function exportCsv() {
    const blob = await exportScreen(request);
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'stockscope-screen.csv';
    link.click();
    URL.revokeObjectURL(url);
  }

  const rows = screenQuery.data?.items ?? [];
  const total = screenQuery.data?.total ?? 0;
  const sectorFilter = state.filters.find((filter) => filter.metric === 'sector');
  const sectorValue = typeof sectorFilter?.value === 'string' ? sectorFilter.value : '';
  const sortMetric = state.sort[0]?.metric ?? defaultState.sort[0]?.metric ?? 'market_cap';
  const sortDir = state.sort[0]?.dir ?? 'desc';

  return (
    <div className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-[320px_1fr]">
        <aside className="space-y-4">
          <div className="rounded border border-slate-200 bg-white p-3">
            <label className="text-sm font-semibold" htmlFor="sector-quick">
              Sector
            </label>
            <select
              id="sector-quick"
              className="mt-1 w-full rounded border border-slate-300 p-2"
              value={sectorValue}
              onChange={(event) => {
                const others = state.filters.filter((filter) => filter.metric !== 'sector');
                const value = event.target.value;
                update({
                  ...state,
                  offset: 0,
                  filters:
                    value.length === 0
                      ? others
                      : [...others, { metric: 'sector', op: 'eq', value }],
                });
              }}
            >
              <option value="">All sectors</option>
              {(sectorsQuery.data?.sectors ?? []).map((sector) => (
                <option key={sector} value={sector}>
                  {sector}
                </option>
              ))}
            </select>
          </div>

          {qualityQuery.data && (
            <div className="rounded border border-slate-200 bg-white p-3 text-sm">
              <h2 className="font-semibold">Data quality</h2>
              <p className="mt-1 text-xs text-slate-500">
                Stale after {qualityQuery.data.stale_after_days} days · generated{' '}
                {new Date(qualityQuery.data.generated_at).toLocaleString()}
              </p>
              <ul className="mt-2 space-y-1">
                {qualityQuery.data.metrics
                  .filter((metric) => metric.stale_count > 0)
                  .sort((a, b) => b.stale_count - a.stale_count)
                  .slice(0, 5)
                  .map((metric) => (
                    <li key={metric.key} className="flex justify-between gap-2">
                      <span className="truncate">{metric.label}</span>
                      <span className="tabular text-amber-700">{metric.stale_count} stale</span>
                    </li>
                  ))}
              </ul>
              {qualityQuery.data.last_refreshes[0] && (
                <div className="mt-2 text-xs text-slate-500">
                  <p>
                    Last refresh: {qualityQuery.data.last_refreshes[0].job} ·{' '}
                    {qualityQuery.data.last_refreshes[0].status}
                  </p>
                  {qualityQuery.data.last_refreshes[0].error && (
                    <p className="text-red-700">{qualityQuery.data.last_refreshes[0].error}</p>
                  )}
                </div>
              )}
            </div>
          )}

          {metricsQuery.isLoading && <p className="text-sm">Loading metrics…</p>}
          <FilterBar
            metrics={metrics}
            filters={state.filters}
            onChange={(filters) => update({ ...state, filters, offset: 0 })}
          />
          <RankingPanel
            metrics={metrics}
            weights={state.weights}
            onChange={(weights) => update({ ...state, weights, offset: 0 })}
          />
          <div className="rounded border border-slate-200 bg-white p-3">
            <h2 className="text-sm font-semibold">Sort</h2>
            <div className="mt-2 flex gap-2">
              <select
                aria-label="Sort metric"
                className="flex-1 rounded border border-slate-300 p-1"
                value={sortMetric}
                onChange={(event) =>
                  update({ ...state, sort: [{ metric: event.target.value, dir: sortDir }] })
                }
              >
                {metrics.map((metric) => (
                  <option key={metric.key} value={metric.key}>
                    {metric.label}
                  </option>
                ))}
              </select>
              <select
                aria-label="Sort direction"
                className="rounded border border-slate-300 p-1"
                value={sortDir}
                onChange={(event) =>
                  update({
                    ...state,
                    sort: [{ metric: sortMetric, dir: event.target.value === 'asc' ? 'asc' : 'desc' }],
                  })
                }
              >
                <option value="desc">Desc</option>
                <option value="asc">Asc</option>
              </select>
            </div>
          </div>
        </aside>

        <section className="min-w-0 space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-semibold">Screener</h1>
              <p className="text-sm text-slate-500">{total} companies match</p>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                className="rounded border border-slate-300 px-3 py-1 text-sm"
                onClick={() => void exportCsv()}
              >
                Export CSV
              </button>
              <button
                type="button"
                className="rounded bg-slate-800 px-3 py-1 text-sm text-white"
                onClick={() => void saveScreen()}
              >
                Save screen
              </button>
              <button
                type="button"
                className="rounded border border-slate-300 px-3 py-1 text-sm disabled:opacity-40"
                disabled={state.offset === 0}
                onClick={() => update({ ...state, offset: Math.max(0, state.offset - state.limit) })}
              >
                Previous
              </button>
              <button
                type="button"
                className="rounded border border-slate-300 px-3 py-1 text-sm disabled:opacity-40"
                disabled={state.offset + state.limit >= total}
                onClick={() => update({ ...state, offset: state.offset + state.limit })}
              >
                Next
              </button>
            </div>
          </div>

          {screenQuery.isError && (
            <p className="rounded bg-red-50 p-3 text-sm text-red-700">
              {screenQuery.error.message}
            </p>
          )}
          {screenQuery.isLoading && <p className="text-sm">Loading companies…</p>}
          <MetricsTable
            rows={rows}
            metrics={metrics}
            onSelect={(ticker) => navigate(`/companies/${ticker}?s=${encodeURIComponent(params.get('s') ?? '')}`)}
          />
        </section>
      </div>
    </div>
  );
}
