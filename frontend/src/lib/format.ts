export function toNumber(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === '') return null;
  const parsed = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function formatMetric(value: string | number | null | undefined, unit: string): string {
  const number = toNumber(value);
  if (number === null) return '\u2014';
  if (unit === 'percent') return `${(number * 100).toFixed(1)}%`;
  if (unit === 'currency') {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      notation: 'compact',
      maximumFractionDigits: 2,
    }).format(number);
  }
  if (unit === 'number' || unit === 'ratio') {
    return new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }).format(number);
  }
  return String(value);
}

export function isStale(asOf: string, staleAfterDays: number): boolean {
  const timestamp = new Date(asOf).getTime();
  if (Number.isNaN(timestamp)) return false;
  return timestamp < Date.now() - staleAfterDays * 86_400_000;
}

export function scoreText(value: number | null): string {
  return value === null ? '\u2014' : value.toFixed(3);
}
