import { useCallback, useEffect, useState } from 'react';
import { z } from 'zod';

import type { Filing } from './schemas';

const STORAGE_KEY = 'stockscope.alerts';

export const alertSchema = z.object({
  id: z.string(),
  ticker: z.string().regex(/^[A-Z0-9.-]{1,16}$/),
  metric: z.string().min(1),
  op: z.enum(['lt', 'lte', 'gt', 'gte']),
  threshold: z.number().finite(),
  createdAt: z.string(),
});
export type Alert = z.infer<typeof alertSchema>;

export const filingAlertSchema = z.object({
  id: z.string(),
  kind: z.literal('filing'),
  ticker: z.string().regex(/^[A-Z0-9.-]{1,16}$/),
  forms: z.array(z.string()).default([]),
  lastSeen: z.string(),
  seenAccessions: z.array(z.string()).default([]),
  createdAt: z.string(),
});
export type FilingAlert = z.infer<typeof filingAlertSchema>;

export type AnyAlert = Alert | FilingAlert;

const alertsSchema = z.array(z.union([alertSchema, filingAlertSchema]));

export function isFilingAlert(alert: AnyAlert): alert is FilingAlert {
  return 'kind' in alert && alert.kind === 'filing';
}

function read(storage: Storage): AnyAlert[] {
  try {
    const raw: unknown = JSON.parse(storage.getItem(STORAGE_KEY) ?? '[]');
    const parsed = alertsSchema.safeParse(raw);
    return parsed.success ? parsed.data : [];
  } catch {
    return [];
  }
}

function write(storage: Storage, alerts: AnyAlert[]): void {
  try {
    storage.setItem(STORAGE_KEY, JSON.stringify(alerts));
  } catch {
    // Keep alerts in memory when storage is unavailable.
  }
}

export function useAlerts() {
  const [alerts, setAlerts] = useState<AnyAlert[]>(() => read(window.localStorage));

  useEffect(() => {
    const sync = (event: StorageEvent) => {
      if (event.key === STORAGE_KEY) setAlerts(read(window.localStorage));
    };
    window.addEventListener('storage', sync);
    return () => window.removeEventListener('storage', sync);
  }, []);

  const update = useCallback((next: AnyAlert[]) => {
    setAlerts(next);
    write(window.localStorage, next);
  }, []);

  const addAlert = useCallback(
    (alert: AnyAlert) => update([...alerts, alert]),
    [alerts, update],
  );

  const remove = useCallback(
    (id: string) => update(alerts.filter((alert) => alert.id !== id)),
    [alerts, update],
  );

  const markFilingSeen = useCallback(
    (id: string, lastSeen: string, accessions: string[]) =>
      update(
        alerts.map((alert) =>
          alert.id === id && isFilingAlert(alert)
            ? {
                ...alert,
                lastSeen,
                seenAccessions: [...new Set([...alert.seenAccessions, ...accessions])],
              }
            : alert,
        ),
      ),
    [alerts, update],
  );

  return { alerts, addAlert, remove, markFilingSeen };
}

export function isTriggered(value: number | null, op: Alert['op'], threshold: number): boolean {
  if (value === null) return false;
  if (op === 'lt') return value < threshold;
  if (op === 'lte') return value <= threshold;
  if (op === 'gt') return value > threshold;
  return value >= threshold;
}

export function matchingFilings(alert: FilingAlert, filings: Filing[]): Filing[] {
  return filings.filter(
    (filing) =>
      filing.ticker === alert.ticker &&
      filing.filing_date.slice(0, 10) >= alert.lastSeen.slice(0, 10) &&
      !alert.seenAccessions.includes(filing.accession_number) &&
      (alert.forms.length === 0 || alert.forms.includes(filing.form)),
  );
}

export function alertNotificationKey(alert: AnyAlert): string {
  if (isFilingAlert(alert)) {
    return `${alert.id}:${alert.lastSeen}:${alert.seenAccessions.join(",")}`;
  }
  return `${alert.id}:${alert.op}:${alert.threshold}`;
}

export function notify(title: string, body: string): void {
  if (typeof Notification === 'undefined' || Notification.permission !== 'granted') return;
  new Notification(title, { body });
}

export async function requestNotificationPermission(): Promise<NotificationPermission> {
  if (typeof Notification === 'undefined') return 'denied';
  return Notification.requestPermission();
}
