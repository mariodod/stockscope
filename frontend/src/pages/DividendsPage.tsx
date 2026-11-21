import { useState } from 'react';
import { Link } from 'react-router-dom';

import { formatMetric } from '../lib/format';
import { useDividends } from '../lib/queries';

export function DividendsPage({
  tickers,
}: {
  tickers: string[];
}) {
  const [days, setDays] = useState(90);
  const [onlySaved, setOnlySaved] = useState(true);
  const query = useDividends(days, onlySaved ? tickers : []);
  const events = query.data ?? [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Dividend calendar</h1>
          <p className="text-sm text-slate-500">Upcoming ex-dividend dates from stored events</p>
        </div>
        <Link to="/" className="text-sm text-sky-700 hover:underline">
          Back to screener
        </Link>
      </div>

      <div className="flex flex-wrap items-center gap-4 rounded border border-slate-200 bg-white p-3 text-sm">
        <label>
          Window (days)
          <input
            type="number"
            min="1"
            max="365"
            className="ml-2 w-20 rounded border border-slate-300 px-2 py-1"
            value={days}
            onChange={(event) => setDays(Number(event.target.value))}
          />
        </label>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={onlySaved}
            onChange={(event) => setOnlySaved(event.target.checked)}
          />
          Only watched or held companies
        </label>
      </div>

      {query.isError && <p className="text-sm text-red-700">{query.error.message}</p>}
      {events.length === 0 ? (
        <p className="rounded border border-slate-200 bg-white p-4 text-sm text-slate-500">
          No upcoming dividend events. Run the dividends ingestion job to populate the calendar.
        </p>
      ) : (
        <div className="overflow-auto rounded border border-slate-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-100 text-xs uppercase">
              <tr>
                <th className="px-3 py-2">Ex date</th>
                <th className="px-3 py-2">Ticker</th>
                <th className="px-3 py-2">Company</th>
                <th className="px-3 py-2">Amount/share</th>
                <th className="px-3 py-2">Pay date</th>
              </tr>
            </thead>
            <tbody>
              {events.map((event) => (
                <tr key={`${event.ticker}-${event.ex_date}`} className="border-t border-slate-100">
                  <td className="px-3 py-2">{event.ex_date}</td>
                  <td className="px-3 py-2">
                    <Link
                      className="text-sky-700 hover:underline"
                      to={`/companies/${event.ticker}`}
                    >
                      {event.ticker}
                    </Link>
                  </td>
                  <td className="px-3 py-2">{event.company_name}</td>
                  <td className="tabular px-3 py-2">
                    {formatMetric(event.amount_per_share, 'currency')}
                  </td>
                  <td className="px-3 py-2">{event.pay_date ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
