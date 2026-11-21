import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
  type VisibilityState,
} from '@tanstack/react-table';
import { useEffect, useState } from 'react';

import { formatMetric, scoreText } from '../lib/format';
import type { CompanySummary, Metric } from '../lib/schemas';

const DESCRIPTIVE = new Set(['sector', 'industry', 'exchange', 'country', 'currency', 'ticker', 'name']);

const helper = createColumnHelper<CompanySummary>();

interface MetricsTableProps {
  rows: CompanySummary[];
  metrics: Metric[];
  onSelect: (ticker: string) => void;
  isWatched: (ticker: string) => boolean;
  onToggleWatch: (ticker: string) => void;
}

export function MetricsTable({
  rows,
  metrics,
  onSelect,
  isWatched,
  onToggleWatch,
}: MetricsTableProps) {
  const [visibility, setVisibility] = useState<VisibilityState>({
    watch: true,
    ticker: true,
    name: true,
    sector: true,
    score: true,
    market_cap: true,
    pe_ratio: true,
    roe: true,
    revenue_growth_yoy: true,
  });

  useEffect(() => {
    setVisibility((current) => {
      const next = { ...current };
      for (const metric of metrics) {
        if (!(metric.key in next)) next[metric.key] = false;
      }
      return next;
    });
  }, [metrics]);

  const columns = [
    helper.display({
      id: 'watch',
      header: '☆',
      enableSorting: false,
      cell: ({ row }) => {
        const ticker = row.original.ticker;
        const watched = isWatched(ticker);
        return (
          <button
            type="button"
            aria-label={`${watched ? 'Unstar' : 'Star'} ${ticker}`}
            title={watched ? 'Remove from watchlist' : 'Add to watchlist'}
            className={watched ? 'text-amber-500' : 'text-slate-300 hover:text-amber-500'}
            onClick={(event) => {
              event.stopPropagation();
              onToggleWatch(ticker);
            }}
            onKeyDown={(event) => event.stopPropagation()}
          >
            {watched ? '★' : '☆'}
          </button>
        );
      },
    }),
    helper.accessor('ticker', { header: 'Ticker', enableSorting: false }),
    helper.accessor('name', { header: 'Company', enableSorting: false }),
    helper.accessor('sector', { header: 'Sector', enableSorting: false }),
    ...metrics
      .filter((metric) => !DESCRIPTIVE.has(metric.key))
      .map((metric) =>
        helper.accessor((row) => row.metrics[metric.key], {
          id: metric.key,
          header: metric.label,
          enableSorting: false,
          cell: (info) => formatMetric(info.getValue(), metric.unit),
        }),
      ),
    helper.accessor('score', {
      header: 'Score',
      enableSorting: false,
      cell: (info) => scoreText(info.getValue()),
    }),
  ];

  // TanStack Table v8 intentionally returns render helpers; they are stable within this component.
  // eslint-disable-next-line react-hooks/incompatible-library
  const table = useReactTable({
    data: rows,
    columns,
    state: { columnVisibility: visibility },
    onColumnVisibilityChange: setVisibility,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <div className="space-y-2">
      <details className="rounded border border-slate-200 bg-white p-2 text-sm">
        <summary className="cursor-pointer font-semibold">Columns</summary>
        <div className="mt-2 flex flex-wrap gap-3">
          {table.getAllLeafColumns().map((column) => (
            <label key={column.id} className="flex items-center gap-1">
              <input
                type="checkbox"
                checked={column.getIsVisible()}
                onChange={column.getToggleVisibilityHandler()}
              />
              {column.id}
            </label>
          ))}
        </div>
      </details>
      <div className="max-h-[620px] overflow-auto rounded border border-slate-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="sticky top-0 bg-slate-100 text-xs uppercase tracking-wide">
            {table.getHeaderGroups().map((group) => (
              <tr key={group.id}>
                {group.headers.map((header) => (
                  <th key={header.id} className="whitespace-nowrap px-3 py-2">
                    {header.isPlaceholder
                      ? null
                      : flexRender(header.column.columnDef.header, header.getContext())}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr
                key={row.id}
                className="cursor-pointer border-t border-slate-100 hover:bg-sky-50"
                tabIndex={0}
                onClick={() => onSelect(row.original.ticker)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') onSelect(row.original.ticker);
                }}
              >
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="tabular whitespace-nowrap px-3 py-2">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td className="px-3 py-6 text-center text-slate-500" colSpan={columns.length}>
                  No companies match these filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
