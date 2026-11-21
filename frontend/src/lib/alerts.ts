import { useCallback } from 'react';
import { z } from 'zod';

import { tickerSchema, type Filing } from './schemas';
import { useStoredState } from './storage';

const STORAGE_KEY = 'stockscope.alerts';

export const alertSchema = z.object({
  id: z.string(),
  ticker: tickerSchema,
  metric: z.string().min(1),
  op: z.enum(['lt', 'lte', 'gt', 'gte']),
  threshold: z.number().finite(),
  createdAt: z.string(),
});
export type Alert = z.infer<typeof alertSchema>;

export const filingAlertSchema = z.object({
  id: z.string(),
  kind: z.literal('filing'),
  ticker: tickerSchema,
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

const EMPTY: never[] = [];

export function useAlerts() {
  const [alerts, setAlerts] = useStoredState<AnyAlert[]>(STORAGE_KEY, alertsSchema, EMPTY);

  const addAlert = useCallback(
    (alert: AnyAlert) => setAlerts((current) => [...current, alert]),
    [setAlerts],
  );

  const remove = useCallback(
    (id: string) => setAlerts((current) => current.filter((alert) => alert.id !== id)),
    [setAlerts],
  );

  const markFilingSeen = useCallback(
    (id: string, lastSeen: string, accessions: string[]) =>
      setAlerts((current) =>
        current.map((alert) =>
          alert.id === id && isFilingAlert(alert)
            ? {
                ...alert,
                lastSeen,
                seenAccessions: [...new Set([...alert.seenAccessions, ...accessions])],
              }
            : alert,
        ),
      ),
    [setAlerts],
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
