// OE-DELIVERY: 2026-11-07-multi-select
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { useState } from 'react';
import AutoTakeoffList from './AutoTakeoffList';
import type { AutoListRow } from './data/auto-takeoff';

const rows: AutoListRow[] = Array.from({ length: 12 }, (_, i) => ({
  id: `c${i + 1}`,
  cat: 'columns',
  des: 'HSS6X6X1/2',
  page: 1,
  valueText: '1',
  value: 1,
  edited: false,
  generated: false,
  label: 'HSS6X6X1/2',
}));

function Harness({ onFocus }: { onFocus: (id: string) => void }) {
  const [sel, setSel] = useState<ReadonlySet<string>>(new Set());
  return (
    <>
      <AutoTakeoffList
        rows={rows}
        currentPage={1}
        selectedIds={sel}
        formatTotal={(ids) => String(ids.length)}
        onFocus={(id) => {
          onFocus(id);
          setSel(new Set([id]));
        }}
        onSelect={(ids) => setSel(new Set(ids))}
        onDelete={() => {}}
        onSetHeight={() => {}}
        onSetProfile={() => {}}
        profileOptions={[]}
      />
      <output data-testid="sel">{[...sel].sort((a, b) => Number(a.slice(1)) - Number(b.slice(1))).join(',')}</output>
    </>
  );
}

function openGroup() {
  // Expand the HSS6X6X1/2 group so its rows show.
  fireEvent.click(screen.getByText('HSS6X6X1/2', { selector: 'span' }));
}

describe('Detected markups: multi-select', () => {
  it('Ctrl+click adds and removes markups one by one', () => {
    const onFocus = vi.fn();
    render(<Harness onFocus={onFocus} />);
    openGroup();
    const r = screen.getAllByTestId('auto-list-row');
    fireEvent.click(r[0]!);
    fireEvent.click(r[2]!, { ctrlKey: true });
    fireEvent.click(r[4]!, { ctrlKey: true });
    expect(screen.getByTestId('sel').textContent).toBe('c1,c3,c5');
    fireEvent.click(r[2]!, { ctrlKey: true });
    expect(screen.getByTestId('sel').textContent).toBe('c1,c5');
    expect(onFocus).toHaveBeenCalledTimes(1);
  });

  it('Shift+click selects the run from markup 1 to markup 10', () => {
    render(<Harness onFocus={() => {}} />);
    openGroup();
    const r = screen.getAllByTestId('auto-list-row');
    fireEvent.click(r[0]!);
    fireEvent.click(r[9]!, { shiftKey: true });
    expect(screen.getByTestId('sel').textContent).toBe('c1,c2,c3,c4,c5,c6,c7,c8,c9,c10');
  });
});
