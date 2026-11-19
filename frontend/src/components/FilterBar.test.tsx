import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import type { Metric } from '../lib/schemas';
import { FilterBar } from './FilterBar';

const metrics: Metric[] = [
  {
    key: 'pe_ratio',
    label: 'P/E',
    category: 'valuation',
    unit: 'ratio',
    direction: 'low',
    formula: 'price / EPS',
    description: '',
    is_derived: true,
  },
];

describe('FilterBar', () => {
  it('adds a filter', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<FilterBar metrics={metrics} filters={[]} onChange={onChange} />);

    expect(screen.getByText('No filters applied.')).toBeTruthy();
    await user.click(screen.getByRole('button', { name: 'Add filter' }));
    expect(onChange).toHaveBeenCalledWith([{ metric: 'pe_ratio', op: 'gte', value: 0 }]);
  });

  it('shows an existing filter with a remove action', () => {
    render(
      <FilterBar
        metrics={metrics}
        filters={[{ metric: 'pe_ratio', op: 'lte', value: 25 }]}
        onChange={vi.fn()}
      />,
    );

    expect(screen.getByLabelText('Filter metric')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Remove' })).toBeTruthy();
  });
});
