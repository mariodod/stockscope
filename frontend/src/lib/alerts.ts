import { useCallback, useEffect, useState } from 'react';
import { z } from 'zod';

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

const alertsSchema = z.array(alertSchema);

function read(storage: Storage): Alert[] {
  try {
    const raw: unknown = JSON.parse(storage.getItem(STORAGE_KEY) ?? '[]');
    const parsed = alertsSchema.safeParse(raw);
    return parsed.success ? parsed.data : [];
  } catch {
    return [];
  }
}

function write(storage: Storage, alerts: Alert[]): void {
  try {
    storage.setItem(STORAGE_KEY, JSON.stringify(alerts));
  } catch {
    // Keep alerts in memory when storage is unavailable.
  }
}

export function useAlerts() {
  const [alerts, setAlerts] = useState<Alert[]>(() => read(window.localStorage));

  useEffect(() => {
    const sync = (event: StorageEvent) => {
      if (event.key === STORAGE_KEY) setAlerts(read(window.localStorage));
    };
    window.addEventListener('storage', sync);
    return () => window.removeEventListener('storage', sync);
  }, []);

  const update = useCallback((next: Alert[]) => {
    setAlerts(next);
    write(window.localStorage, next);
  }, []);

  const add = useCallback(
    (alert: Alert) => update([...alerts, alert]),
    [alerts, update],
  );

  const remove = useCallback(
    (id: string) => update(alerts.filter((alert) => alert.id !== id)),
    [alerts, update],
  );

  return { alerts, add, remove };
}

export function isTriggered(value: number | null, op: Alert['op'], threshold: number): boolean {
  if (value === null) return false;
  if (op === 'lt') return value < threshold;
  if (op === 'lte') return value <= threshold;
  if (op === 'gt') return value > threshold;
  return value >= threshold;
}
