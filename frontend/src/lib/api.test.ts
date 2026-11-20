import { afterEach, describe, expect, it, vi } from 'vitest';
import { z } from 'zod';

import { apiGet, ApiError } from './api';

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
