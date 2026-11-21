import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';

import { formatMetric, toNumber } from '../lib/format';
import { useCompanies } from '../lib/queries';
import { holdingSchema, type Holding } from '../lib/portfolio';

function HoldingRow({
  holding,
  company,
  onRemove,
}: {
  holding: Holding;
  company: ReturnType<typeof useCompanies>[number]['data'];
  onRemove: (ticker: string) => void;
}) {
  const priceMetric = company?.latest_metrics.find((metric) => metric.metric_key === 'price');
  const price = toNumber(priceMetric?.value);
  const cost = holding.shares * holding.costBasis;
  const value = price === null ? null : holding.shares * price;
  const pnl = value === null ? null : value - cost;

  return (
    <tr className="border-t border-slate-100">
      <td className="px-3 py-2">
        <Link className="text-sky-700 hover:underline" to={`/companies/${holding.ticker}`}>
          {holding.ticker}
        </Link>
      </td>
      <td className="px-3 py-2">{company?.name ?? 'â€¦'}</td>
      <td className="tabular px-3 py-2">{holding.shares}</td>
      <td className="tabular px-3 py-2">{formatMetric(holding.costBasis, 'currency')}</td>
      <td className="tabular px-3 py-2">{value === null ? 'â€”' : formatMetric(value, 'currency')}</td>
      <td
        className={`tabular px-3 py-2 ${pnl !== null && pnl < 0 ? 'text-red-700' : 'text-green-700'}`}
      >
        {pnl === null ? 'â€”' : formatMetric(pnl, 'currency')}
      </td>
      <td className="px-3 py-2">
        <button
          type="button"
          className="text-sm text-red-600"
          onClick={() => onRemove(holding.ticker)}
        >
          Remove
        </button>
      </td>
    </tr>
  );
}

export function PortfolioPage({
  holdings,
  onAdd,
  onRemove,
}: {
  holdings: Holding[];
  onAdd: (holding: Holding) => void;
  onRemove: (ticker: string) => void;
}) {
  const [ticker, setTicker] = useState('');
  const [shares, setShares] = useState('1');
  const [costBasis, setCostBasis] = useState('0');
  const [error, setError] = useState('');
  const companies = useCompanies(holdings.map((holding) => holding.ticker));

  const priced = holdings.flatMap((holding, index) => {
    const company = companies[index]?.data;
    const price = toNumber(
      company?.latest_metrics.find((metric) => metric.metric_key === 'price')?.value,
    );
    if (price === null) return [];
    return [{ holding, company, value: holding.shares * price }];
  });
  const totalValue = priced.reduce((sum, row) => sum + row.value, 0);
  const totalCost = priced.reduce(
    (sum, row) => sum + row.holding.shares * row.holding.costBasis,
    0,
  );
  const totalPnl = totalValue - totalCost;
  const allocation = new Map<string, number>();
  for (const row of priced) {
    const sector = row.company?.sector ?? 'Unknown';
    allocation.set(sector, (allocation.get(sector) ?? 0) + row.value);
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    const parsed = holdingSchema.safeParse({
      ticker: ticker.trim().toUpperCase(),
      shares: Number(shares),
      costBasis: Number(costBasis),
      addedAt: new Date().toISOString(),
    });
    if (!parsed.success) {
      setError('Enter a valid ticker, a positive number of shares and a non-negative cost.');
      return;
    }
    setError('');
    onAdd(parsed.data);
    setTicker('');
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Portfolio</h1>
          <p className="text-sm text-slate-500">Saved in this browser only</p>
        </div>
        <Link to="/" className="text-sm text-sky-700 hover:underline">
          Back to screener
        </Link>
      </div>

      {holdings.length > 0 && (
        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded border border-slate-200 bg-white p-3">
            <p className="text-xs uppercase text-slate-500">Market value</p>
            <p className="tabular text-xl">{formatMetric(totalValue, 'currency')}</p>
          </div>
          <div className="rounded border border-slate-200 bg-white p-3">
            <p className="text-xs uppercase text-slate-500">Unrealised P/L</p>
            <p className={`tabular text-xl ${totalPnl < 0 ? 'text-red-700' : 'text-green-700'}`}>
              {formatMetric(totalPnl, 'currency')}
            </p>
          </div>
          <div className="rounded border border-slate-200 bg-white p-3">
            <p className="text-xs uppercase text-slate-500">Allocation</p>
            <ul className="mt-1 space-y-1 text-sm">
              {[...allocation.entries()].map(([sector, value]) => (
                <li key={sector} className="flex justify-between">
                  <span>{sector}</span>
                  <span className="tabular">
                    {totalValue > 0 ? `${((value / totalValue) * 100).toFixed(1)}%` : 'â€”'}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      <form
        onSubmit={submit}
        className="flex flex-wrap items-end gap-3 rounded border border-slate-200 bg-white p-3"
      >
        <label className="text-sm">
          Ticker
          <input
            className="ml-2 rounded border border-slate-300 px-2 py-1"
            value={ticker}
            onChange={(event) => setTicker(event.target.value)}
          />
        </label>
        <label className="text-sm">
          Shares
          <input
            type="number"
            min="0"
            step="any"
            className="ml-2 w-24 rounded border border-slate-300 px-2 py-1"
            value={shares}
            onChange={(event) => setShares(event.target.value)}
          />
        </label>
        <label className="text-sm">
          Cost per share
          <input
            type="number"
            min="0"
            step="any"
            className="ml-2 w-28 rounded border border-slate-300 px-2 py-1"
            value={costBasis}
            onChange={(event) => setCostBasis(event.target.value)}
          />
        </label>
        <button type="submit" className="rounded bg-slate-800 px-3 py-1 text-sm text-white">
          Add holding
        </button>
        {error && <p className="w-full text-sm text-red-700">{error}</p>}
      </form>

      {holdings.length === 0 ? (
        <p className="rounded border border-slate-200 bg-white p-4 text-sm text-slate-500">
          No holdings yet. Add one above to track value and unrealised P/L.
        </p>
      ) : (
        <div className="overflow-auto rounded border border-slate-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-100 text-xs uppercase">
              <tr>
                <th className="px-3 py-2">Ticker</th>
                <th className="px-3 py-2">Company</th>
                <th className="px-3 py-2">Shares</th>
                <th className="px-3 py-2">Cost/share</th>
                <th className="px-3 py-2">Value</th>
                <th className="px-3 py-2">Unrealised P/L</th>
                <th className="px-3 py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {holdings.map((holding, index) => (
                <HoldingRow
                  key={holding.ticker}
                  holding={holding}
                  company={companies[index]?.data}
                  onRemove={onRemove}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
