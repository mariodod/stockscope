import { useCallback, useEffect, useState } from 'react';
import { z } from 'zod';

const STORAGE_KEY = 'stockscope.portfolio';

export const holdingSchema = z.object({
  ticker: z.string().regex(/^[A-Z0-9.-]{1,16}$/),
  shares: z.number().positive(),
  costBasis: z.number().nonnegative(),
  addedAt: z.string(),
});
export type Holding = z.infer<typeof holdingSchema>;

const portfolioSchema = z.array(holdingSchema);

function read(storage: Storage): Holding[] {
  try {
    const raw: unknown = JSON.parse(storage.getItem(STORAGE_KEY) ?? '[]');
    const parsed = portfolioSchema.safeParse(raw);
    return parsed.success ? parsed.data : [];
  } catch {
    return [];
  }
}

function write(storage: Storage, holdings: Holding[]): void {
  try {
    storage.setItem(STORAGE_KEY, JSON.stringify(holdings));
  } catch {
    // Storage can be unavailable; keep the portfolio in memory.
  }
}

export function usePortfolio() {
  const [holdings, setHoldings] = useState<Holding[]>(() => read(window.localStorage));

  useEffect(() => {
    const sync = (event: StorageEvent) => {
      if (event.key === STORAGE_KEY) setHoldings(read(window.localStorage));
    };
    window.addEventListener('storage', sync);
    return () => window.removeEventListener('storage', sync);
  }, []);

  const update = useCallback((next: Holding[]) => {
    setHoldings(next);
    write(window.localStorage, next);
  }, []);

  const add = useCallback(
    (holding: Holding) => {
      const withoutTicker = holdings.filter((item) => item.ticker !== holding.ticker);
      update([...withoutTicker, holding]);
    },
    [holdings, update],
  );

  const remove = useCallback(
    (ticker: string) => update(holdings.filter((item) => item.ticker !== ticker)),
    [holdings, update],
  );

  return { holdings, add, remove };
}
