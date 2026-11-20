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
    const parsed = z
      .object({ detail: z.union([z.string(), z.array(z.unknown())]) })
      .safeParse(raw);
    if (!parsed.success) throw new ApiError(`${response.status} request failed`);
    const detail = parsed.data.detail;
    throw new ApiError(
      typeof detail === 'string' ? detail : detail.map((item) => JSON.stringify(item)).join('; '),
    );
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
