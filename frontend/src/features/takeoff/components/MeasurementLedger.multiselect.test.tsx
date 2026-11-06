// OE-DELIVERY: 2026-11-07-multi-select
import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { useState } from 'react';
import { MeasurementLedger } from './MeasurementLedger';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type M = any;

const ms: M[] = Array.from({ length: 12 }, (_, i) => ({
  id: `m${String(i + 1).padStart(2, '0')}`,
  type: 'count',
  points: [{ x: 10 * i, y: 10 }],
  value: 1,
  unit: 'pcs',
  label: '1',
  annotation: `Column ${String(i + 1).padStart(2, '0')}`,
  page: 1,
  group: 'Columns',
}));

function Harness({ onRow }: { onRow: (id: string) => void }) {
  const [sel, setSel] = useState<ReadonlySet<string>>(new Set());
  return (
    <>
      <MeasurementLedger
        measurements={ms}
        groupColorMap={{ Columns: '#16A34A' }}
        selectedIds={sel}
        onToggleSelect={(id) =>
          setSel((prev) => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id);
            else next.add(id);
            return next;
          })
        }
        onToggleSelectAll={() => {}}
        onRowClick={(m: M) => onRow(m.id)}
      />
      <output data-testid="sel">{[...sel].sort((a, b) => Number(a.slice(1)) - Number(b.slice(1))).join(',')}</output>
    </>
  );
}

function rowsOf() {
  return screen.getAllByRole('row').filter((r) => r.getAttribute('aria-selected') !== null);
}

describe('Markups list: multi-select', () => {
  it('Ctrl+click toggles rows; a plain click still opens the markup', () => {
    const onRow = vi.fn();
    render(<Harness onRow={onRow} />);
    const r = rowsOf();
    fireEvent.click(r[0]!);
    expect(onRow).toHaveBeenCalledWith('m01');
    fireEvent.click(r[1]!, { ctrlKey: true });
    fireEvent.click(r[3]!, { ctrlKey: true });
    expect(screen.getByTestId('sel').textContent).toBe('m02,m04');
    fireEvent.click(r[1]!, { metaKey: true });
    expect(screen.getByTestId('sel').textContent).toBe('m04');
  });

  it('Shift+click selects the run of rows', () => {
    render(<Harness onRow={() => {}} />);
    const r = rowsOf();
    fireEvent.click(r[0]!);
    fireEvent.click(r[9]!, { shiftKey: true });
    expect(screen.getByTestId('sel').textContent).toBe('m01,m02,m03,m04,m05,m06,m07,m08,m09,m10');
  });
});
