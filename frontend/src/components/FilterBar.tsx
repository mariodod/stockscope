import { useState } from 'react';

import {
  filterConditionSchema,
  type FilterCondition,
  type FilterOp,
  type Metric,
} from '../lib/schemas';

const OPERATORS: FilterOp[] = [
  'eq',
  'neq',
  'gt',
  'gte',
  'lt',
  'lte',
  'between',
  'in',
  'is_null',
];

function initialValue(row: FilterCondition): string {
  if (Array.isArray(row.value)) return row.value.join(', ');
  if (row.value === null) return '';
  return String(row.value);
}

function parseValue(op: FilterOp, text: string): FilterCondition['value'] {
  if (op === 'is_null') return text === 'true';
  const parts = text
    .split(',')
    .map((part) => part.trim())
    .filter((part) => part.length > 0);
  if (op === 'between') return parts.map(Number);
  if (op === 'in') return parts;
  const number = Number(text);
  return text.length > 0 && Number.isFinite(number) ? number : text;
}

interface FilterRowProps {
  row: FilterCondition;
  metrics: Metric[];
  onChange: (row: FilterCondition) => void;
  onRemove: () => void;
}

function FilterRow({ row, metrics, onChange, onRemove }: FilterRowProps) {
  const [draft, setDraft] = useState(() => initialValue(row));

  function update(next: Partial<FilterCondition>) {
    const candidate = { ...row, ...next };
    const parsed = filterConditionSchema.safeParse(candidate);
    if (parsed.success) onChange(parsed.data);
  }

  return (
    <div className="flex flex-wrap items-center gap-2 rounded border border-slate-200 bg-white p-2">
      <select
        aria-label="Filter metric"
        className="rounded border border-slate-300 px-2 py-1"
        value={row.metric}
        onChange={(event) => update({ metric: event.target.value })}
      >
        {metrics.map((metric) => (
          <option key={metric.key} value={metric.key}>
            {metric.label}
          </option>
        ))}
      </select>
      <select
        aria-label="Filter operator"
        className="rounded border border-slate-300 px-2 py-1"
        value={row.op}
        onChange={(event) => {
          const op = filterConditionSchema.shape.op.parse(event.target.value);
          setDraft(initialValue({ ...row, op, value: parseValue(op, draft) }));
          update({ op, value: parseValue(op, draft) });
        }}
      >
        {OPERATORS.map((op) => (
          <option key={op} value={op}>
            {op}
          </option>
        ))}
      </select>
      {row.op === 'is_null' ? (
        <select
          aria-label="Filter value"
          className="rounded border border-slate-300 px-2 py-1"
          value={draft}
          onChange={(event) => {
            setDraft(event.target.value);
            update({ value: event.target.value === 'true' });
          }}
        >
          <option value="true">is null</option>
          <option value="false">is not null</option>
        </select>
      ) : (
        <input
          aria-label="Filter value"
          className="w-48 rounded border border-slate-300 px-2 py-1"
          value={draft}
          placeholder={row.op === 'between' ? '10, 25' : row.op === 'in' ? 'a, b' : 'value'}
          onChange={(event) => {
            setDraft(event.target.value);
            update({ value: parseValue(row.op, event.target.value) });
          }}
        />
      )}
      <button type="button" className="text-sm text-red-600" onClick={onRemove}>
        Remove
      </button>
    </div>
  );
}

interface FilterBarProps {
  metrics: Metric[];
  filters: FilterCondition[];
  onChange: (filters: FilterCondition[]) => void;
}

export function FilterBar({ metrics, filters, onChange }: FilterBarProps) {
  return (
    <section className="space-y-2" aria-label="Filters">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">Filters</h2>
        <button
          type="button"
          className="rounded bg-slate-800 px-3 py-1 text-sm text-white"
          onClick={() => {
            const first = metrics[0];
            if (first === undefined) return;
            onChange([...filters, filterConditionSchema.parse({ metric: first.key, op: 'gte', value: 0 })]);
          }}
        >
          Add filter
        </button>
      </div>
      {filters.map((row, index) => (
        <FilterRow
          key={index}
          row={row}
          metrics={metrics}
          onChange={(updated) => onChange(filters.map((item, i) => (i === index ? updated : item)))}
          onRemove={() => onChange(filters.filter((_, i) => i !== index))}
        />
      ))}
      {filters.length === 0 && <p className="text-sm text-slate-500">No filters applied.</p>}
    </section>
  );
}
