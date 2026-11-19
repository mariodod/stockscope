import { describe, expect, it } from 'vitest';

import { defaultState, readState, stateToRequest, writeState } from './state';

describe('shareable screen state', () => {
  it('round-trips through a URL parameter', () => {
    const state = {
      ...defaultState,
      filters: [{ metric: 'pe_ratio', op: 'lte' as const, value: 25 }],
      weights: { roe: 0.7, pe_ratio: 0.3 },
      offset: 25,
    };

    expect(readState(writeState(state))).toEqual(state);
  });

  it('falls back to defaults for invalid or missing state', () => {
    expect(readState(null)).toEqual(defaultState);
    expect(readState('not json')).toEqual(defaultState);
    expect(readState('{"filters":"wrong"}')).toEqual(defaultState);
  });

  it('omits ranking when no weights are selected', () => {
    expect(stateToRequest(defaultState).ranking).toBeNull();
  });
});
