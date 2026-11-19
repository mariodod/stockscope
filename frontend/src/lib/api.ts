import { z } from 'zod';

const API_BASE = import.meta.env.VITE_API_URL ?? '';

export class ApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(path: string, schema: z.ZodType<T>, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  const raw: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const parsed = z.object({ detail: z.string() }).safeParse(raw);
    throw new ApiError(parsed.success ? parsed.data.detail : `${response.status} request failed`);
  }
  return schema.parse(raw);
}

export function apiGet<T>(path: string, schema: z.ZodType<T>): Promise<T> {
  return request(path, schema);
}

export function apiPost<T>(path: string, schema: z.ZodType<T>, body: unknown): Promise<T> {
  return request(path, schema, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}
