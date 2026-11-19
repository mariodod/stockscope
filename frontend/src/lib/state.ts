import { z } from 'zod';

import {
  filterConditionSchema,
  screenRequestSchema,
  sortSpecSchema,
  type ScreenRequest,
} from './schemas';

export const screenStateSchema = z.object({
  filters: z.array(filterConditionSchema),
  sort: z.array(sortSpecSchema),
  weights: z.record(z.string(), z.number()),
  limit: z.number(),
  offset: z.number(),
});
export type ScreenState = z.infer<typeof screenStateSchema>;

export const defaultState: ScreenState = {
  filters: [],
  sort: [{ metric: 'market_cap', dir: 'desc' }],
  weights: {},
  limit: 25,
  offset: 0,
};

export function readState(param: string | null): ScreenState {
  if (param === null) return defaultState;
  try {
    const raw: unknown = JSON.parse(param);
    const parsed = screenStateSchema.safeParse(raw);
    return parsed.success ? parsed.data : defaultState;
  } catch {
    return defaultState;
  }
}

export function writeState(state: ScreenState): string {
  return JSON.stringify(state);
}

export function stateToRequest(state: ScreenState, columns: string[] = []): ScreenRequest {
  return screenRequestSchema.parse({
    filters: state.filters,
    sort: state.sort,
    columns,
    ranking: Object.keys(state.weights).length > 0 ? { weights: state.weights } : null,
    limit: state.limit,
    offset: state.offset,
  });
}
