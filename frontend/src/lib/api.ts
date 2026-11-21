import { z } from 'zod';

const API_BASE = import.meta.env.VITE_API_URL ?? '';

export class ApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

function errorMessage(status: number, raw: unknown): string {
  const parsed = z
    .object({ detail: z.union([z.string(), z.array(z.unknown())]) })
    .safeParse(raw);
  if (!parsed.success) return `${status} request failed`;
  const detail = parsed.data.detail;
  return typeof detail === 'string'
    ? detail
    : detail.map((item) => JSON.stringify(item)).join('; ');
}

async function request<T>(path: string, schema: z.ZodType<T>, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  const raw: unknown = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(errorMessage(response.status, raw));
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

export async function exportScreen(body: unknown): Promise<Blob> {
  const response = await fetch(`${API_BASE}/api/v1/screen/export`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const raw: unknown = await response.json().catch(() => null);
    throw new ApiError(errorMessage(response.status, raw));
  }
  return response.blob();
}
