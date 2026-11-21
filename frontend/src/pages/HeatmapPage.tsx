import { useState } from 'react';
import { Link } from 'react-router-dom';

import { useSectorPerformance } from '../lib/queries';

function tileColor(change: number): string {
  const intensity = Math.min(Math.abs(change) / 15, 0.85);
  return change >= 0
    ? `rgba(22, 163, 74, ${0.12 + intensity})`
    : `rgba(220, 38, 38, ${0.12 + intensity})`;
}

export function HeatmapPage() {
  const [days, setDays] = useState(90);
  const query = useSectorPerformance(days);
  const sectors = query.data ?? [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Sector heatmap</h1>
          <p className="text-sm text-slate-500">Price return and valuation by sector</p>
        </div>
        <Link to="/" className="text-sm text-sky-700 hover:underline">
          Back to screener
        </Link>
      </div>

      <div className="rounded border border-slate-200 bg-white p-3 text-sm">
        <label>
          Lookback (days)
          <input
            type="number"
            min="1"
            max="3650"
            className="ml-2 w-24 rounded border border-slate-300 px-2 py-1"
            value={days}
            onChange={(event) => setDays(Number(event.target.value))}
          />
        </label>
      </div>

      {query.isError && <p className="text-sm text-red-700">{query.error.message}</p>}
      {sectors.length === 0 ? (
        <p className="rounded border border-slate-200 bg-white p-4 text-sm text-slate-500">
          No sector history available. Backfill price history to populate the heatmap.
        </p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {sectors.map((sector) => {
            const state = {
              filters: [{ metric: 'sector', op: 'eq', value: sector.sector }],
              sort: [{ metric: 'market_cap', dir: 'desc' }],
              weights: {},
              limit: 25,
              offset: 0,
            };
            return (
              <Link
                key={sector.sector}
                to={`/?s=${encodeURIComponent(JSON.stringify(state))}`}
                className="rounded border border-slate-200 p-4"
                style={{ backgroundColor: tileColor(sector.return_pct) }}
              >
                <p className="font-semibold">{sector.sector}</p>
                <p className="tabular text-2xl">{sector.return_pct}%</p>
                <p className="mt-2 text-xs text-slate-600">
                  {sector.companies} companies · avg P/E{' '}
                  {sector.avg_pe === null ? '—' : sector.avg_pe}
                </p>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
