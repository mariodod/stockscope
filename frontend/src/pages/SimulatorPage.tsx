import { useState, type FormEvent } from 'react';
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
import { Link } from 'react-router-dom';
import type { z } from 'zod';

import { apiPost, ApiError } from '../lib/api';
import { simulationResultSchema } from '../lib/schemas';

function defaultStart(): string {
  const date = new Date();
  date.setFullYear(date.getFullYear() - 5);
  return date.toISOString().slice(0, 10);
}

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

type Result = z.infer<typeof simulationResultSchema>;

export function SimulatorPage() {
  const [tickers, setTickers] = useState('AAPL');
  const [start, setStart] = useState(defaultStart);
  const [end, setEnd] = useState(today);
  const [strategy, setStrategy] = useState('lump_sum');
  const [initial, setInitial] = useState('10000');
  const [contribution, setContribution] = useState('100');
  const [reinvest, setReinvest] = useState(true);
  const [benchmark, setBenchmark] = useState('SPY');
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError('');
    setLoading(true);
    try {
      const parsed = await apiPost('/api/v1/simulate', simulationResultSchema, {
        tickers: tickers
          .split(',')
          .map((item) => item.trim().toUpperCase())
          .filter(Boolean),
        start,
        end,
        initial: Number(initial),
        contribution: Number(contribution),
        strategy,
        dividend_reinvestment: reinvest,
        benchmark: benchmark.trim().toUpperCase() || null,
      });
      setResult(parsed);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : 'Simulation failed');
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Returns simulator</h1>
          <p className="text-sm text-slate-500">
            Compare lump sum and dollar-cost averaging using stored daily prices
          </p>
        </div>
        <Link to="/" className="text-sm text-sky-700 hover:underline">
          Back to screener
        </Link>
      </div>

      <form
        onSubmit={(event) => void submit(event)}
        className="grid gap-3 rounded border border-slate-200 bg-white p-3 md:grid-cols-3"
      >
        <label className="text-sm">
          Tickers (comma separated)
          <input
            className="ml-2 rounded border border-slate-300 px-2 py-1"
            value={tickers}
            onChange={(event) => setTickers(event.target.value)}
          />
        </label>
        <label className="text-sm">
          Start
          <input
            type="date"
            className="ml-2 rounded border border-slate-300 px-2 py-1"
            value={start}
            onChange={(event) => setStart(event.target.value)}
          />
        </label>
        <label className="text-sm">
          End
          <input
            type="date"
            className="ml-2 rounded border border-slate-300 px-2 py-1"
            value={end}
            onChange={(event) => setEnd(event.target.value)}
          />
        </label>
        <label className="text-sm">
          Strategy
          <select
            className="ml-2 rounded border border-slate-300 px-2 py-1"
            value={strategy}
            onChange={(event) => setStrategy(event.target.value)}
          >
            <option value="lump_sum">Lump sum</option>
            <option value="dca">Dollar-cost averaging</option>
          </select>
        </label>
        <label className="text-sm">
          Initial investment
          <input
            type="number"
            min="0"
            className="ml-2 w-28 rounded border border-slate-300 px-2 py-1"
            value={initial}
            onChange={(event) => setInitial(event.target.value)}
          />
        </label>
        <label className="text-sm">
          Monthly contribution
          <input
            type="number"
            min="0"
            className="ml-2 w-28 rounded border border-slate-300 px-2 py-1"
            value={contribution}
            onChange={(event) => setContribution(event.target.value)}
          />
        </label>
        <label className="text-sm">
          Benchmark
          <input
            className="ml-2 w-24 rounded border border-slate-300 px-2 py-1"
            value={benchmark}
            onChange={(event) => setBenchmark(event.target.value)}
          />
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={reinvest}
            onChange={(event) => setReinvest(event.target.checked)}
          />
          Reinvest dividends
        </label>
        <button
          type="submit"
          disabled={loading}
          className="rounded bg-slate-800 px-3 py-1 text-sm text-white disabled:opacity-50"
        >
          {loading ? 'Running…' : 'Run simulation'}
        </button>
        {error && <p className="text-sm text-red-700 md:col-span-3">{error}</p>}
      </form>

      {result && (
        <div className="space-y-4">
          <div className="grid gap-3 md:grid-cols-4">
            <div className="rounded border border-slate-200 bg-white p-3">
              <p className="text-xs uppercase text-slate-500">Final value</p>
              <p className="tabular text-xl">${result.performance.final_value.toLocaleString()}</p>
            </div>
            <div className="rounded border border-slate-200 bg-white p-3">
              <p className="text-xs uppercase text-slate-500">Total return</p>
              <p className="tabular text-xl">{result.performance.total_return_pct}%</p>
            </div>
            <div className="rounded border border-slate-200 bg-white p-3">
              <p className="text-xs uppercase text-slate-500">Annualised</p>
              <p className="tabular text-xl">{result.performance.annualised_return_pct}%</p>
            </div>
            <div className="rounded border border-slate-200 bg-white p-3">
              <p className="text-xs uppercase text-slate-500">Max drawdown</p>
              <p className="tabular text-xl">{result.performance.max_drawdown_pct}%</p>
            </div>
          </div>

          <div className="rounded border border-slate-200 bg-white p-4">
            <h2 className="mb-3 text-sm font-semibold">Portfolio value over time</h2>
            <ResponsiveContainer width="100%" height={320}>
              <LineChart data={result.series}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="value" stroke="#0284c7" dot={false} />
                <Line type="monotone" dataKey="benchmark_value" stroke="#f59e0b" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}
