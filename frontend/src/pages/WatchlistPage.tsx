import { Link } from 'react-router-dom';

import { formatMetric } from '../lib/format';
import { useCompany } from '../lib/queries';
const SUMMARY_KEYS = ['market_cap', 'pe_ratio', 'roe', 'revenue_growth_yoy'];

function WatchlistRow({
  ticker,
  onRemove,
}: {
  ticker: string;
  onRemove: (ticker: string) => void;
}) {
  const { data: company, isError } = useCompany(ticker);
  const metrics = new Map(
    (company?.latest_metrics ?? []).map((item) => [item.metric_key, item]),
  );

  return (
    <tr className="border-t border-slate-100">
      <td className="px-3 py-2">
        <Link className="text-sky-700 hover:underline" to={`/companies/${ticker}`}>
          {ticker}
        </Link>
      </td>
      <td className="px-3 py-2">{company?.name ?? (isError ? 'Unavailable' : '…')}</td>
      {SUMMARY_KEYS.map((key) => {
        const metric = metrics.get(key);
        return (
          <td key={key} className="tabular px-3 py-2">
            {metric ? formatMetric(metric.value, metric.unit) : '\u2014'}
          </td>
        );
      })}
      <td className="px-3 py-2">
        <button type="button" className="text-sm text-red-600" onClick={() => onRemove(ticker)}>
          Remove
        </button>
      </td>
    </tr>
  );
}

export function WatchlistPage({
  tickers,
  onRemove,
}: {
  tickers: string[];
  onRemove: (ticker: string) => void;
}) {

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Watchlist</h1>
          <p className="text-sm text-slate-500">Saved in this browser only</p>
        </div>
        <Link to="/" className="text-sm text-sky-700 hover:underline">
          Back to screener
        </Link>
      </div>

      {tickers.length === 0 ? (
        <p className="rounded border border-slate-200 bg-white p-4 text-sm text-slate-500">
          No watched companies yet. Star a company in the screener to add it here.
        </p>
      ) : (
        <div className="overflow-auto rounded border border-slate-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-100 text-xs uppercase">
              <tr>
                <th className="px-3 py-2">Ticker</th>
                <th className="px-3 py-2">Company</th>
                {SUMMARY_KEYS.map((key) => (
                  <th key={key} className="px-3 py-2">
                    {key.replaceAll('_', ' ')}
                  </th>
                ))}
                <th className="px-3 py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {tickers.map((ticker) => (
                <WatchlistRow key={ticker} ticker={ticker} onRemove={onRemove} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
