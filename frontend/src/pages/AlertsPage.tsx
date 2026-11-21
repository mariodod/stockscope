import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';

import {
  alertNotificationKey,
  alertSchema,
  filingAlertSchema,
  isFilingAlert,
  isTriggered,
  matchingFilings,
  notify,
  requestNotificationPermission,
  type Alert,
  type AnyAlert,
  type FilingAlert,
} from '../lib/alerts';
import { toNumber } from '../lib/format';
import type { Filing } from '../lib/schemas';
import { useCompanies, useFilings } from '../lib/queries';

function MetricAlertRow({
  alert,
  company,
  onRemove,
}: {
  alert: Alert;
  company: ReturnType<typeof useCompanies>[number]['data'];
  onRemove: (id: string) => void;
}) {
  const metric = company?.latest_metrics.find((item) => item.metric_key === alert.metric);
  const value = toNumber(metric?.value);
  const triggered = isTriggered(value, alert.op, alert.threshold);

  return (
    <tr className="border-t border-slate-100">
      <td className="px-3 py-2">{alert.ticker}</td>
      <td className="px-3 py-2">Metric</td>
      <td className="px-3 py-2">
        {alert.metric} {alert.op} {alert.threshold}
      </td>
      <td className="tabular px-3 py-2">{value ?? '\u2014'}</td>
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

function FilingAlertRow({
  alert,
  filings,
  onRemove,
  onMarkSeen,
}: {
  alert: FilingAlert;
  filings: Filing[];
  onRemove: (id: string) => void;
  onMarkSeen: (id: string, lastSeen: string, accessions: string[]) => void;
}) {
  const newFilings = matchingFilings(alert, filings);
  const latest = newFilings
    .map((filing) => filing.filing_date.slice(0, 10))
    .sort()
    .at(-1);

  return (
    <tr className="border-t border-slate-100">
      <td className="px-3 py-2">{alert.ticker}</td>
      <td className="px-3 py-2">Filing</td>
      <td className="px-3 py-2">
        {alert.forms.length > 0 ? alert.forms.join(', ') : 'All forms'}
      </td>
      <td className="px-3 py-2">
        {newFilings.length > 0 ? (
          <span className="rounded bg-red-100 px-2 py-1 text-xs text-red-800">
            {newFilings.length} new
          </span>
        ) : (
          <span className="text-xs text-slate-500">None since {alert.lastSeen.slice(0, 10)}</span>
        )}
      </td>
      <td className="px-3 py-2">
        {latest && (
          <button
            type="button"
            className="text-sm text-sky-700"
            onClick={() =>
              onMarkSeen(
                alert.id,
                latest,
                newFilings.map((filing) => filing.accession_number),
              )
            }
          >
            Mark seen
          </button>
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
  onAddAlert,
  onRemove,
  onMarkFilingSeen,
}: {
  alerts: AnyAlert[];
  onAddAlert: (alert: AnyAlert) => void;
  onRemove: (id: string) => void;
  onMarkFilingSeen: (id: string, lastSeen: string, accessions: string[]) => void;
}) {
  const [ticker, setTicker] = useState('');
  const [metric, setMetric] = useState('pe_ratio');
  const [op, setOp] = useState<Alert['op']>('lte');
  const [threshold, setThreshold] = useState('20');
  const [forms, setForms] = useState('');
  const [error, setError] = useState('');
  const [permission, setPermission] = useState<NotificationPermission>(
    typeof Notification === 'undefined' ? 'denied' : Notification.permission,
  );
  const notified = useRef(new Set<string>());

  const metricAlerts = useMemo(
    () => alerts.filter((alert): alert is Alert => !isFilingAlert(alert)),
    [alerts],
  );
  const filingAlerts = useMemo(() => alerts.filter(isFilingAlert), [alerts]);
  const metricTickers = useMemo(() => metricAlerts.map((alert) => alert.ticker), [metricAlerts]);
  const filingTickers = useMemo(() => filingAlerts.map((alert) => alert.ticker), [filingAlerts]);
  const companyQueries = useCompanies(metricTickers);
  const filingsQuery = useFilings(30, filingTickers);
  const filings = useMemo(() => filingsQuery.data ?? [], [filingsQuery.data]);

  useEffect(() => {
    metricAlerts.forEach((alert, index) => {
      const metricValue = toNumber(
        companyQueries[index]?.data?.latest_metrics.find(
          (item) => item.metric_key === alert.metric,
        )?.value,
      );
      const key = alertNotificationKey(alert);
      if (isTriggered(metricValue, alert.op, alert.threshold) && !notified.current.has(key)) {
        notified.current.add(key);
        notify('Stockscope alert', `${alert.ticker}: ${alert.metric} ${alert.op} ${alert.threshold}`);
      }
    });
    filingAlerts.forEach((alert) => {
      const count = matchingFilings(
        alert,
        filings.filter((filing) => filing.ticker === alert.ticker),
      ).length;
      const key = alertNotificationKey(alert);
      if (count > 0 && !notified.current.has(key)) {
        notified.current.add(key);
        notify('Stockscope filing alert', `${alert.ticker}: ${count} new filing(s)`);
      }
    });
  }, [metricAlerts, filingAlerts, companyQueries, filings]);

  function submitMetric(event: FormEvent) {
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
    onAddAlert(parsed.data);
    setTicker('');
  }

  function submitFiling(event: FormEvent) {
    event.preventDefault();
    const parsed = filingAlertSchema.safeParse({
      id: crypto.randomUUID(),
      kind: 'filing',
      ticker: ticker.trim().toUpperCase(),
      forms: forms
        .split(',')
        .map((form) => form.trim().toUpperCase())
        .filter(Boolean),
      lastSeen: new Date().toISOString().slice(0, 10),
      seenAccessions: [],
      createdAt: new Date().toISOString(),
    });
    if (!parsed.success) {
      setError('Enter a valid ticker for the filing alert.');
      return;
    }
    setError('');
    onAddAlert(parsed.data);
    setTicker('');
    setForms('');
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Alerts</h1>
          <p className="text-sm text-slate-500">
            Metric thresholds and new SEC filings, saved in this browser
          </p>
        </div>
        <div className="flex gap-3">
          {permission !== 'granted' && (
            <button
              type="button"
              className="text-sm text-sky-700 hover:underline"
              onClick={() => void requestNotificationPermission().then(setPermission)}
            >
              Enable notifications
            </button>
          )}
          <Link to="/" className="text-sm text-sky-700 hover:underline">
            Back to screener
          </Link>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <form
          onSubmit={submitMetric}
          className="flex flex-wrap items-end gap-3 rounded border border-slate-200 bg-white p-3 text-sm"
        >
          <h2 className="w-full font-semibold">Metric threshold</h2>
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
        </form>

        <form
          onSubmit={submitFiling}
          className="flex flex-wrap items-end gap-3 rounded border border-slate-200 bg-white p-3 text-sm"
        >
          <h2 className="w-full font-semibold">New SEC filing</h2>
          <label>
            Ticker
            <input
              className="ml-2 rounded border border-slate-300 px-2 py-1"
              value={ticker}
              onChange={(event) => setTicker(event.target.value)}
            />
          </label>
          <label>
            Forms (optional)
            <input
              className="ml-2 rounded border border-slate-300 px-2 py-1"
              placeholder="10-K, 8-K"
              value={forms}
              onChange={(event) => setForms(event.target.value)}
            />
          </label>
          <button type="submit" className="rounded bg-slate-800 px-3 py-1 text-white">
            Add filing alert
          </button>
        </form>
      </div>
      {error && <p className="text-sm text-red-700">{error}</p>}

      {alerts.length === 0 ? (
        <p className="rounded border border-slate-200 bg-white p-4 text-sm text-slate-500">
          No alerts yet. Add a metric threshold or a filing watch.
        </p>
      ) : (
        <div className="overflow-auto rounded border border-slate-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-100 text-xs uppercase">
              <tr>
                <th className="px-3 py-2">Ticker</th>
                <th className="px-3 py-2">Type</th>
                <th className="px-3 py-2">Condition</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Acknowledge</th>
                <th className="px-3 py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {metricAlerts.map((alert, index) => (
                <MetricAlertRow
                  key={alert.id}
                  alert={alert}
                  company={companyQueries[index]?.data}
                  onRemove={onRemove}
                />
              ))}
              {filingAlerts.map((alert) => (
                <FilingAlertRow
                  key={alert.id}
                  alert={alert}
                  filings={filings.filter((filing) => filing.ticker === alert.ticker)}
                  onRemove={onRemove}
                  onMarkSeen={onMarkFilingSeen}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
