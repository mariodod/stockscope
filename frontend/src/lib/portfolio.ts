import { useCallback, useEffect, useState } from 'react';
import { z } from 'zod';

const STORAGE_KEY = 'stockscope.portfolio';

export const transactionSchema = z.object({
  id: z.string(),
  ticker: z.string().regex(/^[A-Z0-9.-]{1,16}$/),
  side: z.enum(['buy', 'sell']),
  shares: z.number().positive(),
  price: z.number().nonnegative(),
  date: z.string(),
});
export type Transaction = z.infer<typeof transactionSchema>;

export const holdingSchema = z.object({
  ticker: z.string().regex(/^[A-Z0-9.-]{1,16}$/),
  shares: z.number().positive(),
  costBasis: z.number().nonnegative(),
  addedAt: z.string(),
});
export type Holding = z.infer<typeof holdingSchema>;

const transactionsSchema = z.array(transactionSchema);
const legacySchema = z.array(holdingSchema);

const tickerPattern = /^[A-Z0-9.-]{1,16}$/;

export function deriveHoldings(transactions: Transaction[]): Holding[] {
  const ordered = [...transactions].sort((a, b) => a.date.localeCompare(b.date));
  const holdings = new Map<string, Holding>();

  for (const transaction of ordered) {
    if (!tickerPattern.test(transaction.ticker)) continue;
    const current = holdings.get(transaction.ticker);
    if (transaction.side === 'buy') {
      if (!current) {
        holdings.set(transaction.ticker, {
          ticker: transaction.ticker,
          shares: transaction.shares,
          costBasis: transaction.price,
          addedAt: transaction.date,
        });
        continue;
      }
      const shares = current.shares + transaction.shares;
      const costBasis =
        (current.shares * current.costBasis + transaction.shares * transaction.price) / shares;
      holdings.set(transaction.ticker, { ...current, shares, costBasis });
      continue;
    }

    if (!current || transaction.shares > current.shares) continue;
    const shares = current.shares - transaction.shares;
    if (shares === 0) holdings.delete(transaction.ticker);
    else holdings.set(transaction.ticker, { ...current, shares });
  }

  return [...holdings.values()];
}

function read(storage: Storage): Transaction[] {
  try {
    const raw: unknown = JSON.parse(storage.getItem(STORAGE_KEY) ?? '[]');
    const parsed = transactionsSchema.safeParse(raw);
    if (parsed.success) return parsed.data;

    const legacy = legacySchema.safeParse(raw);
    if (legacy.success) {
      return legacy.data.map((holding) => ({
        id: `legacy-${holding.ticker}`,
        ticker: holding.ticker,
        side: 'buy' as const,
        shares: holding.shares,
        price: holding.costBasis,
        date: holding.addedAt,
      }));
    }
    return [];
  } catch {
    return [];
  }
}

function write(storage: Storage, transactions: Transaction[]): void {
  try {
    storage.setItem(STORAGE_KEY, JSON.stringify(transactions));
  } catch {
    // Keep transactions in memory when storage is unavailable.
  }
}

export function usePortfolio() {
  const [transactions, setTransactions] = useState<Transaction[]>(() => read(window.localStorage));
  const holdings = deriveHoldings(transactions);

  useEffect(() => {
    write(window.localStorage, transactions);
  }, [transactions]);

  useEffect(() => {
    const sync = (event: StorageEvent) => {
      if (event.key === STORAGE_KEY) setTransactions(read(window.localStorage));
    };
    window.addEventListener('storage', sync);
    return () => window.removeEventListener('storage', sync);
  }, []);

  const addTransaction = useCallback(
    (transaction: Transaction) => setTransactions((current) => [...current, transaction]),
    [],
  );

  const closePosition = useCallback((ticker: string) => {
    setTransactions((current) => {
      const holding = deriveHoldings(current).find((item) => item.ticker === ticker);
      if (!holding) return current;
      return [
        ...current,
        {
          id: crypto.randomUUID(),
          ticker,
          side: 'sell' as const,
          shares: holding.shares,
          price: 0,
          date: new Date().toISOString(),
        },
      ];
    });
  }, []);

  return { transactions, holdings, addTransaction, closePosition };
}
