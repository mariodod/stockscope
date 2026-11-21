import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';

import { deriveHoldings, usePortfolio, type Transaction } from './portfolio';

function transaction(side: 'buy' | 'sell', shares: number, price: number, date: string): Transaction {
  return { id: `${side}-${date}-${shares}`, ticker: 'AAPL', side, shares, price, date };
}

describe('portfolio transactions', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('derives holdings from buys and sells with average cost', () => {
    const holdings = deriveHoldings([
      transaction('buy', 10, 100, '2026-01-01'),
      transaction('buy', 10, 200, '2026-02-01'),
      transaction('sell', 5, 300, '2026-03-01'),
    ]);

    expect(holdings).toHaveLength(1);
    expect(holdings[0]?.shares).toBe(15);
    expect(holdings[0]?.costBasis).toBe(150);
  });

  it('ignores sells larger than the position and removes closed positions', () => {
    const holdings = deriveHoldings([
      transaction('buy', 5, 100, '2026-01-01'),
      transaction('sell', 10, 120, '2026-02-01'),
      transaction('sell', 5, 120, '2026-03-01'),
    ]);

    expect(holdings).toEqual([]);
  });

  it('stores transactions and closes positions', () => {
    const { result } = renderHook(() => usePortfolio());

    act(() => result.current.addTransaction(transaction('buy', 10, 100, '2026-01-01')));
    expect(result.current.holdings[0]?.shares).toBe(10);

    act(() => result.current.closePosition('AAPL'));
    expect(result.current.holdings).toEqual([]);
    expect(result.current.transactions).toHaveLength(2);
    expect(JSON.parse(window.localStorage.getItem('stockscope.portfolio') ?? '[]')).toHaveLength(2);
  });

  it('migrates old holdings into buy transactions', () => {
    window.localStorage.setItem(
      'stockscope.portfolio',
      JSON.stringify([{ ticker: 'MSFT', shares: 3, costBasis: 250, addedAt: '2025-06-01' }]),
    );

    const { result } = renderHook(() => usePortfolio());

    expect(result.current.transactions).toEqual([
      {
        id: 'legacy-MSFT',
        ticker: 'MSFT',
        side: 'buy',
        shares: 3,
        price: 250,
        date: '2025-06-01',
      },
    ]);
    expect(result.current.holdings[0]?.shares).toBe(3);
  });

  it('ignores malformed stored data', () => {
    window.localStorage.setItem('stockscope.portfolio', '{"ticker":"AAPL"}');

    const { result } = renderHook(() => usePortfolio());

    expect(result.current.transactions).toEqual([]);
  });
});
