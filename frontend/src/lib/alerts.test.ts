import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';

import { isTriggered, useAlerts } from './alerts';

describe('alerts', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('adds and removes alerts in local storage', () => {
    const { result } = renderHook(() => useAlerts());
    const alert = {
      id: '1',
      ticker: 'AAPL',
      metric: 'pe_ratio',
      op: 'lte' as const,
      threshold: 20,
      createdAt: '2026-01-01',
    };

    act(() => result.current.add(alert));
    expect(result.current.alerts).toEqual([alert]);
    expect(JSON.parse(window.localStorage.getItem('stockscope.alerts') ?? '[]')).toEqual([alert]);

    act(() => result.current.remove('1'));
    expect(result.current.alerts).toEqual([]);
  });

  it('evaluates threshold comparisons', () => {
    expect(isTriggered(15, 'lte', 20)).toBe(true);
    expect(isTriggered(25, 'lte', 20)).toBe(false);
    expect(isTriggered(25, 'gte', 20)).toBe(true);
    expect(isTriggered(null, 'lt', 20)).toBe(false);
  });

  it('ignores malformed stored alerts', () => {
    window.localStorage.setItem('stockscope.alerts', '{}');

    const { result } = renderHook(() => useAlerts());

    expect(result.current.alerts).toEqual([]);
  });
});
