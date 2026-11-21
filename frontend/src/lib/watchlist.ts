import { useCallback } from 'react';
import { z } from 'zod';

import { tickerSchema } from './schemas';
import { useStoredState } from './storage';

const STORAGE_KEY = 'stockscope.watchlist';
const watchlistSchema = z.array(tickerSchema);

export function useWatchlist() {
  const [tickers, setTickers] = useStoredState<string[]>(STORAGE_KEY, watchlistSchema, []);

  const toggle = useCallback(
    (ticker: string) =>
      setTickers((current) =>
        current.includes(ticker)
          ? current.filter((item) => item !== ticker)
          : [...current, ticker],
      ),
    [setTickers],
  );

  const remove = useCallback(
    (ticker: string) => setTickers((current) => current.filter((item) => item !== ticker)),
    [setTickers],
  );

  return { tickers, isWatched: (ticker: string) => tickers.includes(ticker), toggle, remove };
}
