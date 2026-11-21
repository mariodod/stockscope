import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';

import { formatMetric, toNumber } from '../lib/format';
import { transactionSchema, type Holding, type Transaction } from '../lib/portfolio';
import { useCompanies } from '../lib/queries';

function HoldingRow({
  holding,
  company,
  contributionPct,
  onClose,
}: {
  holding: Holding;
  company: ReturnType<typeof useCompanies>[number]['data'];
  contributionPct: number | null;
  onClose: (ticker: string) => void;
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
      <td className="px-3 py-2">{company?.name ?? '\u2026'}</td>
      <td className="tabular px-3 py-2">{holding.shares}</td>
      <td className="tabular px-3 py-2">{formatMetric(holding.costBasis, 'currency')}</td>
      <td className="tabular px-3 py-2">
        {value === null ? '\u2014' : formatMetric(value, 'currency')}
      </td>
      <td
        className={`tabular px-3 py-2 ${pnl !== null && pnl < 0 ? 'text-red-700' : 'text-green-700'}`}
      >
        {pnl === null ? '\u2014' : formatMetric(pnl, 'currency')}
      </td>
      <td className="tabular px-3 py-2">
        {contributionPct === null ? '\u2014' : `${contributionPct.toFixed(2)}%`}
      </td>
      <td className="px-3 py-2">
        <button
          type="button"
          className="text-sm text-red-600"
          onClick={() => onClose(holding.ticker)}
        >
          Close
        </button>
      </td>
    </tr>
  );
}

export function PortfolioPage({
  holdings,
  transactions,
  onAddTransaction,
  onClosePosition,
}: {
  holdings: Holding[];
  transactions: Transaction[];
  onAddTransaction: (transaction: Transaction) => void;
  onClosePosition: (ticker: string) => void;
}) {
  const [ticker, setTicker] = useState('');
  const [side, setSide] = useState<'buy' | 'sell'>('buy');
  const [shares, setShares] = useState('1');
  const [price, setPrice] = useState('0');
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [error, setError] = useState('');
  const companies = useCompanies(holdings.map((holding) => holding.ticker));

  const priced = holdings.flatMap((holding, index) => {
    const company = companies[index]?.data;
    const current = toNumber(
      company?.latest_metrics.find((metric) => metric.metric_key === 'price')?.value,
    );
    if (current === null) return [];
    return [{ holding, company, value: holding.shares * current }];
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
    const parsed = transactionSchema.safeParse({
      id: crypto.randomUUID(),
      ticker: ticker.trim().toUpperCase(),
      side,
      shares: Number(shares),
      price: Number(price),
      date: new Date(date).toISOString(),
    });
    if (!parsed.success) {
      setError('Enter a valid ticker, positive shares, a non-negative price and a date.');
      return;
    }
    if (parsed.data.side === 'sell') {
      const held = holdings.find((holding) => holding.ticker === parsed.data.ticker);
      if (!held || parsed.data.shares > held.shares) {
        setError('Cannot sell more shares than are held.');
        return;
      }
    }
    setError('');
    onAddTransaction(parsed.data);
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
                    {totalValue > 0 ? `${((value / totalValue) * 100).toFixed(1)}%` : '\u2014'}
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
          Side
          <select
            className="ml-2 rounded border border-slate-300 px-2 py-1"
            value={side}
            onChange={(event) => setSide(event.target.value as 'buy' | 'sell')}
          >
            <option value="buy">Buy</option>
            <option value="sell">Sell</option>
          </select>
        </label>
        <label className="text-sm">
          Shares
          <input
            type="number"
            min="0"
            step="any"
            className="ml-2 w-20 rounded border border-slate-300 px-2 py-1"
            value={shares}
            onChange={(event) => setShares(event.target.value)}
          />
        </label>
        <label className="text-sm">
          Price/share
          <input
            type="number"
            min="0"
            step="any"
            className="ml-2 w-24 rounded border border-slate-300 px-2 py-1"
            value={price}
            onChange={(event) => setPrice(event.target.value)}
          />
        </label>
        <label className="text-sm">
          Date
          <input
            type="date"
            className="ml-2 rounded border border-slate-300 px-2 py-1"
            value={date}
            onChange={(event) => setDate(event.target.value)}
          />
        </label>
        <button type="submit" className="rounded bg-slate-800 px-3 py-1 text-sm text-white">
          Add transaction
        </button>
        {error && <p className="w-full text-sm text-red-700">{error}</p>}
      </form>

      {holdings.length === 0 ? (
        <p className="rounded border border-slate-200 bg-white p-4 text-sm text-slate-500">
          No holdings yet. Add a buy transaction to start tracking value and unrealised P/L.
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
                <th className="px-3 py-2">Contribution</th>
                <th className="px-3 py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {holdings.map((holding, index) => {
                const row = priced.find((item) => item.holding.ticker === holding.ticker);
                const pnl = row ? row.value - holding.shares * holding.costBasis : null;
                return (
                  <HoldingRow
                    key={holding.ticker}
                    holding={holding}
                    company={companies[index]?.data}
                    contributionPct={pnl !== null && totalCost > 0 ? (pnl / totalCost) * 100 : null}
                    onClose={onClosePosition}
                  />
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <div className="rounded border border-slate-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-semibold">Transaction history</h2>
        {transactions.length === 0 ? (
          <p className="text-sm text-slate-500">No transactions recorded.</p>
        ) : (
          <div className="overflow-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-100 text-xs uppercase">
                <tr>
                  <th className="px-3 py-2">Date</th>
                  <th className="px-3 py-2">Ticker</th>
                  <th className="px-3 py-2">Side</th>
                  <th className="px-3 py-2">Shares</th>
                  <th className="px-3 py-2">Price</th>
                </tr>
              </thead>
              <tbody>
                {[...transactions]
                  .sort((a, b) => b.date.localeCompare(a.date))
                  .map((transaction) => (
                    <tr key={transaction.id} className="border-t border-slate-100">
                      <td className="px-3 py-2">{transaction.date.slice(0, 10)}</td>
                      <td className="px-3 py-2">{transaction.ticker}</td>
                      <td className="px-3 py-2">{transaction.side}</td>
                      <td className="tabular px-3 py-2">{transaction.shares}</td>
                      <td className="tabular px-3 py-2">
                        {formatMetric(transaction.price, 'currency')}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
