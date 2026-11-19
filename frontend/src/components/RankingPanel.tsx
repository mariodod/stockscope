import type { Metric } from '../lib/schemas';

interface RankingPanelProps {
  metrics: Metric[];
  weights: Record<string, number>;
  onChange: (weights: Record<string, number>) => void;
}

export function RankingPanel({ metrics, weights, onChange }: RankingPanelProps) {
  const rankable = metrics.filter((metric) => metric.direction === 'high' || metric.direction === 'low');

  return (
    <details className="rounded border border-slate-200 bg-white p-3" open>
      <summary className="cursor-pointer text-sm font-semibold">Composite ranking</summary>
      <p className="mt-2 text-xs text-slate-500">
        Weights are normalized automatically. Missing values score neutrally.
      </p>
      <div className="mt-3 grid max-h-60 grid-cols-2 gap-2 overflow-auto md:grid-cols-3">
        {rankable.map((metric) => {
          const enabled = Object.hasOwn(weights, metric.key);
          return (
            <label key={metric.key} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={enabled}
                onChange={(event) => {
                  const next = { ...weights };
                  if (event.target.checked) next[metric.key] = 1;
                  else delete next[metric.key];
                  onChange(next);
                }}
              />
              <span className="flex-1 truncate" title={metric.label}>
                {metric.label}
              </span>
              {enabled && (
                <input
                  aria-label={`${metric.label} weight`}
                  type="number"
                  min="0"
                  step="0.1"
                  className="w-16 rounded border border-slate-300 px-1 py-0.5"
                  value={weights[metric.key] ?? 0}
                  onChange={(event) => {
                    const value = Number(event.target.value);
                    if (!Number.isFinite(value) || value < 0) return;
                    onChange({ ...weights, [metric.key]: value });
                  }}
                />
              )}
            </label>
          );
        })}
      </div>
    </details>
  );
}
