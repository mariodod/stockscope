import { useCallback, useEffect, useState } from 'react';
import { z } from 'zod';

const STORAGE_KEY = 'stockscope.watchlist';
const tickerSchema = z.string().regex(/^[A-Z0-9.-]{1,16}$/);
const watchlistSchema = z.array(tickerSchema);

function read(storage: Storage): string[] {
  try {
    const raw: unknown = JSON.parse(storage.getItem(STORAGE_KEY) ?? '[]');
    const parsed = watchlistSchema.safeParse(raw);
    return parsed.success ? [...new Set(parsed.data)] : [];
  } catch {
    return [];
  }
}

function write(storage: Storage, tickers: string[]): void {
  try {
    storage.setItem(STORAGE_KEY, JSON.stringify(tickers));
  } catch {
    // Storage can be unavailable (private mode); the watchlist stays in memory.
  }
}

export function useWatchlist() {
  const [tickers, setTickers] = useState<string[]>(() => read(window.localStorage));

  useEffect(() => {
    const sync = (event: StorageEvent) => {
      if (event.key === STORAGE_KEY) setTickers(read(window.localStorage));
    };
    window.addEventListener('storage', sync);
    return () => window.removeEventListener('storage', sync);
  }, []);

  const update = useCallback((next: string[]) => {
    const unique = [...new Set(next)];
    setTickers(unique);
    write(window.localStorage, unique);
  }, []);

  const toggle = useCallback(
    (ticker: string) => {
      update(tickers.includes(ticker) ? tickers.filter((item) => item !== ticker) : [...tickers, ticker]);
    },
    [tickers, update],
  );

  const remove = useCallback(
    (ticker: string) => update(tickers.filter((item) => item !== ticker)),
    [tickers, update],
  );

  return { tickers, isWatched: (ticker: string) => tickers.includes(ticker), toggle, remove };
}
