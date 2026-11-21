import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import {
  alertNotificationKey,
  isFilingAlert,
  isTriggered,
  matchingFilings,
  notify,
  useAlerts,
} from './alerts';

describe('alerts', () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.unstubAllGlobals();
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

    act(() => result.current.addAlert(alert));
    expect(result.current.alerts).toEqual([alert]);
    expect(JSON.parse(window.localStorage.getItem('stockscope.alerts') ?? '[]')).toEqual([alert]);

    act(() => result.current.remove('1'));
    expect(result.current.alerts).toEqual([]);
  });

  it('stores filing alerts and updates their seen date', () => {
    const { result } = renderHook(() => useAlerts());
    const filing = {
      id: '2',
      kind: 'filing' as const,
      ticker: 'MSFT',
      forms: ['10-K'],
      lastSeen: '2026-01-01',
      seenAccessions: [],
      createdAt: '2026-01-01',
    };

    act(() => result.current.addAlert(filing));
    expect(result.current.alerts[0] && isFilingAlert(result.current.alerts[0])).toBe(true);

    act(() => result.current.markFilingSeen('2', '2026-02-01', ['acc-1']));
    const stored = result.current.alerts[0];
    expect(stored && isFilingAlert(stored) && stored.lastSeen).toBe('2026-02-01');
    expect(stored && isFilingAlert(stored) && stored.seenAccessions).toEqual(['acc-1']);
  });

  it('evaluates threshold comparisons', () => {
    expect(isTriggered(15, 'lte', 20)).toBe(true);
    expect(isTriggered(25, 'lte', 20)).toBe(false);
    expect(isTriggered(25, 'gte', 20)).toBe(true);
    expect(isTriggered(null, 'lt', 20)).toBe(false);
  });

  it('matches only relevant filings and changes notification key on acknowledgement', () => {
    const alert = {
      id: '3',
      kind: 'filing' as const,
      ticker: 'MSFT',
      forms: ['10-K'],
      lastSeen: '2026-01-01',
      seenAccessions: [],
      createdAt: '2026-01-01',
    };
    const filings = [
      {
        ticker: 'MSFT',
        company_name: 'Microsoft',
        accession_number: '1',
        form: '10-K',
        filing_date: '2026-02-01',
        primary_document: null,
      },
      {
        ticker: 'MSFT',
        company_name: 'Microsoft',
        accession_number: '2',
        form: '8-K',
        filing_date: '2026-03-01',
        primary_document: null,
      },
    ];

    const sameDay = {
      ticker: 'MSFT',
      company_name: 'Microsoft',
      accession_number: '3',
      form: '10-K',
      filing_date: '2026-01-01',
      primary_document: null,
    };
    const matched = matchingFilings(alert, [...filings, sameDay]);
    expect(matched.map((filing) => filing.accession_number)).toEqual(['1', '3']);
    expect(alertNotificationKey(alert)).toBe('3:2026-01-01:');
    expect(alertNotificationKey({ ...alert, seenAccessions: ['1'] })).toBe('3:2026-01-01:1');
  });

  it('only sends browser notifications when permission is granted', () => {
    const constructor = vi.fn();
    vi.stubGlobal('Notification', Object.assign(constructor, { permission: 'default' }));
    notify('title', 'body');
    expect(constructor).not.toHaveBeenCalled();

    vi.stubGlobal('Notification', Object.assign(vi.fn(), { permission: 'granted' }));
    notify('title', 'body');
    expect(vi.mocked(Notification)).toHaveBeenCalledWith('title', { body: 'body' });
  });

  it('ignores malformed stored alerts', () => {
    window.localStorage.setItem('stockscope.alerts', '{}');

    const { result } = renderHook(() => useAlerts());

    expect(result.current.alerts).toEqual([]);
  });
});
