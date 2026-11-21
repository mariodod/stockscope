import { afterEach, describe, expect, it, vi } from 'vitest';
import { z } from 'zod';

import { apiGet, ApiError, exportScreen } from './api';

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('api error shapes', () => {
  it('surfaces string details', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: 'Bad metric' }), {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    );

    await expect(apiGet('/x', z.object({}))).rejects.toMatchObject({
      name: ApiError.name,
      message: 'Bad metric',
    });
  });

  it('downloads CSV exports', async () => {
    const blob = new Blob(['ticker,name\nAAA,Alpha\n'], { type: 'text/csv' });
    const fetchMock = vi.fn().mockResolvedValue(new Response(blob, { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    const result = await exportScreen({ filters: [], sort: [], limit: 50, offset: 0 });

    expect(result.size).toBeGreaterThan(0);
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/screen/export',
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('surfaces list-shaped validation details', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: [{ msg: 'Value error, invalid filter' }] }), {
          status: 422,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    );

    await expect(apiGet('/x', z.object({}))).rejects.toThrow('invalid filter');
  });
});
