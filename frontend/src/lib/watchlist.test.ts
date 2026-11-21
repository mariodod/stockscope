import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';

import { useWatchlist } from './watchlist';

describe('watchlist', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('toggles tickers and persists them', () => {
    const { result } = renderHook(() => useWatchlist());

    act(() => result.current.toggle('AAPL'));
    expect(result.current.tickers).toEqual(['AAPL']);
    expect(result.current.isWatched('AAPL')).toBe(true);
    expect(window.localStorage.getItem('stockscope.watchlist')).toBe('["AAPL"]');

    act(() => result.current.toggle('MSFT'));
    expect(result.current.tickers).toEqual(['AAPL', 'MSFT']);

    act(() => result.current.toggle('AAPL'));
    expect(result.current.tickers).toEqual(['MSFT']);

    act(() => result.current.remove('MSFT'));
    expect(result.current.tickers).toEqual([]);
  });

  it('ignores malformed stored data', () => {
    window.localStorage.setItem('stockscope.watchlist', '{"ticker":"AAPL"}');

    const { result } = renderHook(() => useWatchlist());

    expect(result.current.tickers).toEqual([]);
  });
});
