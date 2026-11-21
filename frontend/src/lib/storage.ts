import { useCallback, useEffect, useState } from 'react';
import type { z } from 'zod';

export type StoredUpdater<T> = T | ((previous: T) => T);

export function useStoredState<T>(
  key: string,
  schema: z.ZodType<T>,
  fallback: T,
  migrate?: (raw: unknown) => T | null,
): readonly [T, (next: StoredUpdater<T>) => void] {
  const load = useCallback((): T => {
    try {
      const raw: unknown = JSON.parse(window.localStorage.getItem(key) ?? 'null');
      const parsed = schema.safeParse(raw);
      if (parsed.success) return parsed.data;
      return migrate?.(raw) ?? fallback;
    } catch {
      return fallback;
    }
  }, [key, schema, fallback, migrate]);

  const [value, setValue] = useState<T>(load);

  useEffect(() => {
    try {
      window.localStorage.setItem(key, JSON.stringify(value));
    } catch {
      // Keep state in memory when storage is unavailable.
    }
  }, [key, value]);

  useEffect(() => {
    const sync = (event: StorageEvent) => {
      if (event.key === key) setValue(load());
    };
    window.addEventListener('storage', sync);
    return () => window.removeEventListener('storage', sync);
  }, [key, load]);

  const update = useCallback((next: StoredUpdater<T>) => {
    setValue((previous) =>
      typeof next === 'function' ? (next as (value: T) => T)(previous) : next,
    );
  }, []);

  return [value, update] as const;
}
