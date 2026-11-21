import { useCallback } from 'react';
import { z } from 'zod';

import { tickerSchema } from './schemas';
import { useStoredState } from './storage';

const STORAGE_KEY = 'stockscope.portfolio';
const EMPTY: never[] = [];

export const transactionSchema = z.object({
  id: z.string(),
  ticker: tickerSchema,
  side: z.enum(['buy', 'sell']),
  shares: z.number().positive(),
  price: z.number().nonnegative(),
  date: z.string(),
});
export type Transaction = z.infer<typeof transactionSchema>;

export const holdingSchema = z.object({
  ticker: tickerSchema,
  shares: z.number().positive(),
  costBasis: z.number().nonnegative(),
  addedAt: z.string(),
});
export type Holding = z.infer<typeof holdingSchema>;

const transactionsSchema = z.array(transactionSchema);
const legacySchema = z.array(holdingSchema);

const migrateLegacy = (raw: unknown): Transaction[] | null => {
  const parsed = legacySchema.safeParse(raw);
  if (!parsed.success) return null;
  return parsed.data.map((holding) => ({
    id: `legacy-${holding.ticker}`,
    ticker: holding.ticker,
    side: 'buy' as const,
    shares: holding.shares,
    price: holding.costBasis,
    date: holding.addedAt,
  }));
};

export function deriveHoldings(transactions: Transaction[]): Holding[] {
  const ordered = [...transactions].sort((a, b) => a.date.localeCompare(b.date));
  const holdings = new Map<string, Holding>();

  for (const transaction of ordered) {
    if (!tickerSchema.safeParse(transaction.ticker).success) continue;
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

export function usePortfolio() {
  const [transactions, setTransactions] = useStoredState<Transaction[]>(
    STORAGE_KEY,
    transactionsSchema,
    EMPTY,
    migrateLegacy,
  );
  const holdings = deriveHoldings(transactions);

  const addTransaction = useCallback(
    (transaction: Transaction) =>
      setTransactions((current) => [...current, transaction]),
    [setTransactions],
  );

  const closePosition = useCallback(
    (ticker: string) =>
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
            price: holding.costBasis,
            date: new Date().toISOString(),
          },
        ];
      }),
    [setTransactions],
  );

  return { transactions, holdings, addTransaction, closePosition };
}
