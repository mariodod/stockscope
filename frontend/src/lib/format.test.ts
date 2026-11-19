import { describe, expect, it } from 'vitest';

import { formatMetric, scoreText, toNumber } from './format';

describe('metric formatting', () => {
  it('parses numbers from API strings and rejects junk', () => {
    expect(toNumber('12.5')).toBe(12.5);
    expect(toNumber(3)).toBe(3);
    expect(toNumber(null)).toBeNull();
    expect(toNumber('n/a')).toBeNull();
  });

  it('formats units by metric type', () => {
    expect(formatMetric(0.234, 'percent')).toBe('23.4%');
    expect(formatMetric(1_500_000_000, 'currency')).toMatch(/^\$1\.5\d?B$/);
    expect(formatMetric('18.25', 'ratio')).toBe('18.25');
    expect(formatMetric(null, 'ratio')).toBe('\u2014');
  });

  it('formats scores to three decimals', () => {
    expect(scoreText(0.8)).toBe('0.800');
    expect(scoreText(null)).toBe('\u2014');
  });
});
