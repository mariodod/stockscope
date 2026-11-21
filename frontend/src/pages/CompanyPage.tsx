import { useMemo } from 'react';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Link, useParams, useSearchParams } from 'react-router-dom';

import { formatMetric, isStale, toNumber } from '../lib/format';
import { useCompany, useDataQuality, usePeers } from '../lib/queries';

const CHART_METRICS = ['revenue', 'ebitda', 'eps_ttm'];

export function CompanyPage() {
  const { ticker } = useParams();
  const [params] = useSearchParams();
  const companyQuery = useCompany(ticker ?? '');
  const qualityQuery = useDataQuality();
  const peersQuery = usePeers(ticker ?? '');
  const staleAfterDays = qualityQuery.data?.stale_after_days ?? 90;
  const detail = companyQuery.data;

  const chartData = useMemo(() => {
    const byDate = new Map<string, Record<string, string | number | null>>();
    for (const point of detail?.history ?? []) {
      if (!CHART_METRICS.includes(point.metric_key)) continue;
      const row = byDate.get(point.as_of_date) ?? { date: point.as_of_date };
      row[point.metric_key] = toNumber(point.value);
      byDate.set(point.as_of_date, row);
    }
    return [...byDate.values()].sort((a, b) => String(a.date).localeCompare(String(b.date)));
  }, [detail]);

  const back = `/?s=${encodeURIComponent(params.get('s') ?? '')}`;

  if (companyQuery.isLoading) return <p className="text-sm">Loading company…</p>;
  if (companyQuery.isError || detail === undefined) {
    return <p className="rounded bg-red-50 p-3 text-sm text-red-700">{companyQuery.error?.message}</p>;
  }

  return (
    <div className="space-y-4">
      <Link to={back} className="text-sm text-sky-700 hover:underline">
        ← Back to screener
      </Link>

      <header className="rounded border border-slate-200 bg-white p-4">
        <h1 className="text-2xl font-semibold">
          {detail.name} <span className="text-slate-400">({detail.ticker})</span>
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          {[detail.sector, detail.industry, detail.exchange, detail.country]
            .filter((value): value is string => value !== null && value.length > 0)
            .join(' · ')}
        </p>
      </header>

      <section className="rounded border border-slate-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-semibold">Fundamentals timeline</h2>
        {chartData.length === 0 ? (
          <p className="text-sm text-slate-500">No revenue, EBITDA or EPS history available.</p>
        ) : (
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="revenue" stroke="#0284c7" dot={false} />
              <Line type="monotone" dataKey="ebitda" stroke="#16a34a" dot={false} />
              <Line type="monotone" dataKey="eps_ttm" stroke="#f59e0b" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </section>

      <section className="rounded border border-slate-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-semibold">Latest metrics</h2>
        <div className="overflow-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-100 text-xs uppercase">
              <tr>
                <th className="px-3 py-2">Metric</th>
                <th className="px-3 py-2">Value</th>
                <th className="px-3 py-2">Period</th>
                <th className="px-3 py-2">Source</th>
                <th className="px-3 py-2">As of</th>
              </tr>
            </thead>
            <tbody>
              {detail.latest_metrics.map((metric) => (
                <tr
                  key={`${metric.metric_key}-${metric.source}-${metric.period}`}
                  className="border-t border-slate-100"
                >
                  <td className="px-3 py-2">{metric.label}</td>
                  <td className="tabular px-3 py-2">
                    {formatMetric(metric.value, metric.unit)}
                  </td>
                  <td className="px-3 py-2">{metric.period}</td>
                  <td className="px-3 py-2">{metric.source}</td>
                  <td className="px-3 py-2">
                    {metric.as_of_date}
                    {isStale(metric.as_of_date, staleAfterDays) && (
                      <span className="ml-2 rounded bg-amber-100 px-1 text-xs text-amber-800">
                        stale
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded border border-slate-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-semibold">Closest sector peers</h2>
        {peersQuery.data?.items.length === 0 || !peersQuery.data ? (
          <p className="text-sm text-slate-500">No sector peers available.</p>
        ) : (
          <div className="overflow-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-100 text-xs uppercase">
                <tr>
                  <th className="px-3 py-2">Ticker</th>
                  <th className="px-3 py-2">Company</th>
                  <th className="px-3 py-2">Market cap</th>
                  <th className="px-3 py-2">P/E</th>
                  <th className="px-3 py-2">ROE</th>
                </tr>
              </thead>
              <tbody>
                {peersQuery.data.items.map((peer) => (
                  <tr key={peer.ticker} className="border-t border-slate-100">
                    <td className="px-3 py-2">
                      <Link
                        className="text-sky-700 hover:underline"
                        to={`/companies/${peer.ticker}`}
                      >
                        {peer.ticker}
                      </Link>
                    </td>
                    <td className="px-3 py-2">{peer.name}</td>
                    <td className="tabular px-3 py-2">
                      {formatMetric(peer.metrics.market_cap, 'currency')}
                    </td>
                    <td className="tabular px-3 py-2">
                      {formatMetric(peer.metrics.pe_ratio, 'ratio')}
                    </td>
                    <td className="tabular px-3 py-2">
                      {formatMetric(peer.metrics.roe, 'percent')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
