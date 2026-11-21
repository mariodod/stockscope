import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';

import { usePortfolio } from './portfolio';

describe('portfolio', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('adds, replaces and removes holdings', () => {
    const { result } = renderHook(() => usePortfolio());
    const holding = { ticker: 'AAPL', shares: 10, costBasis: 150, addedAt: '2026-01-01' };

    act(() => result.current.add(holding));
    expect(result.current.holdings).toEqual([holding]);

    act(() => result.current.add({ ...holding, shares: 20 }));
    expect(result.current.holdings).toEqual([{ ...holding, shares: 20 }]);

    act(() => result.current.remove('AAPL'));
    expect(result.current.holdings).toEqual([]);
  });

  it('ignores malformed stored holdings', () => {
    window.localStorage.setItem('stockscope.portfolio', '{"ticker":"AAPL"}');

    const { result } = renderHook(() => usePortfolio());

    expect(result.current.holdings).toEqual([]);
  });
});
