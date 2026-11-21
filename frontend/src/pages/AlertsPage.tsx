import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';

import { alertSchema, isTriggered, type Alert } from '../lib/alerts';
import { toNumber } from '../lib/format';
import { useCompany } from '../lib/queries';

function AlertRow({ alert, onRemove }: { alert: Alert; onRemove: (id: string) => void }) {
  const { data: company } = useCompany(alert.ticker);
  const metric = company?.latest_metrics.find((item) => item.metric_key === alert.metric);
  const value = toNumber(metric?.value);
  const triggered = isTriggered(value, alert.op, alert.threshold);

  return (
    <tr className="border-t border-slate-100">
      <td className="px-3 py-2">{alert.ticker}</td>
      <td className="px-3 py-2">{alert.metric}</td>
      <td className="px-3 py-2">
        {alert.op} {alert.threshold}
      </td>
      <td className="tabular px-3 py-2">{value ?? '—'}</td>
      <td className="px-3 py-2">
        {triggered ? (
          <span className="rounded bg-red-100 px-2 py-1 text-xs text-red-800">Triggered</span>
        ) : (
          <span className="text-xs text-slate-500">Watching</span>
        )}
      </td>
      <td className="px-3 py-2">
        <button type="button" className="text-sm text-red-600" onClick={() => onRemove(alert.id)}>
          Remove
        </button>
      </td>
    </tr>
  );
}

export function AlertsPage({
  alerts,
  onAdd,
  onRemove,
}: {
  alerts: Alert[];
  onAdd: (alert: Alert) => void;
  onRemove: (id: string) => void;
}) {
  const [ticker, setTicker] = useState('');
  const [metric, setMetric] = useState('pe_ratio');
  const [op, setOp] = useState<Alert['op']>('lte');
  const [threshold, setThreshold] = useState('20');
  const [error, setError] = useState('');

  function submit(event: FormEvent) {
    event.preventDefault();
    const parsed = alertSchema.safeParse({
      id: crypto.randomUUID(),
      ticker: ticker.trim().toUpperCase(),
      metric: metric.trim(),
      op,
      threshold: Number(threshold),
      createdAt: new Date().toISOString(),
    });
    if (!parsed.success) {
      setError('Enter a valid ticker, metric and numeric threshold.');
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
          <h1 className="text-xl font-semibold">Alerts</h1>
          <p className="text-sm text-slate-500">In-app thresholds, saved in this browser</p>
        </div>
        <Link to="/" className="text-sm text-sky-700 hover:underline">
          Back to screener
        </Link>
      </div>

      <form
        onSubmit={submit}
        className="flex flex-wrap items-end gap-3 rounded border border-slate-200 bg-white p-3 text-sm"
      >
        <label>
          Ticker
          <input
            className="ml-2 rounded border border-slate-300 px-2 py-1"
            value={ticker}
            onChange={(event) => setTicker(event.target.value)}
          />
        </label>
        <label>
          Metric key
          <input
            className="ml-2 rounded border border-slate-300 px-2 py-1"
            value={metric}
            onChange={(event) => setMetric(event.target.value)}
          />
        </label>
        <label>
          Condition
          <select
            className="ml-2 rounded border border-slate-300 px-2 py-1"
            value={op}
            onChange={(event) => setOp(event.target.value as Alert['op'])}
          >
            <option value="lt">&lt;</option>
            <option value="lte">≤</option>
            <option value="gt">&gt;</option>
            <option value="gte">≥</option>
          </select>
        </label>
        <label>
          Threshold
          <input
            type="number"
            step="any"
            className="ml-2 w-24 rounded border border-slate-300 px-2 py-1"
            value={threshold}
            onChange={(event) => setThreshold(event.target.value)}
          />
        </label>
        <button type="submit" className="rounded bg-slate-800 px-3 py-1 text-white">
          Add alert
        </button>
        {error && <p className="w-full text-red-700">{error}</p>}
      </form>

      {alerts.length === 0 ? (
        <p className="rounded border border-slate-200 bg-white p-4 text-sm text-slate-500">
          No alerts yet. Add a metric threshold to watch a company.
        </p>
      ) : (
        <div className="overflow-auto rounded border border-slate-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-100 text-xs uppercase">
              <tr>
                <th className="px-3 py-2">Ticker</th>
                <th className="px-3 py-2">Metric</th>
                <th className="px-3 py-2">Condition</th>
                <th className="px-3 py-2">Current</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {alerts.map((alert) => (
                <AlertRow key={alert.id} alert={alert} onRemove={onRemove} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
