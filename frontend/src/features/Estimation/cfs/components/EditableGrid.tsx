// DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
// Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
/**
 * EditableGrid — a spreadsheet-like table: editable input cells on the
 * left (the workbook's "USER INPUTS"), read-only computed cells on the
 * right (the workbook's "AUTO CALCULATED"), plus row add/delete and an
 * optional per-row action (e.g. the calculation-detail popup).
 */

import { useState } from 'react';
import clsx from 'clsx';
import { AlertTriangle, ListOrdered, Plus, Trash2 } from 'lucide-react';
import type { Cell } from '../engine/types';

export interface GridColumn<T> {
  key: string;
  header: string;
  /** input | computed */
  kind: 'input' | 'computed';
  input?: 'text' | 'number' | 'select';
  options?: string[];
  /** datalist suggestions for text inputs (e.g. 493 materials) */
  suggestions?: string[];
  width?: number;
  align?: 'left' | 'right' | 'center';
  step?: string;
  placeholder?: string;
  get: (row: T) => string | number | null | undefined;
  set?: (row: T, v: string) => T;
  compute?: (computed: Record<string, Cell>, row: T) => Cell | string | null;
  title?: (row: T) => string | undefined;
}

interface Props<T extends { id: string }> {
  columns: GridColumn<T>[];
  rows: T[];
  computedFor: (row: T) => { values: Record<string, Cell | string | null>; errors: string[]; invalid?: string | null };
  onChange: (rows: T[]) => void;
  onAdd: () => T;
  addLabel: string;
  onDetail?: (row: T) => void;
  detailTitle?: string;
  testId?: string;
}

export function fmtCell(v: Cell | string | null | undefined): string {
  if (v == null || v === '') return '—';
  if (typeof v === 'number') {
    if (!Number.isFinite(v)) return '—';
    return Math.abs(v) >= 1000 ? v.toLocaleString('en-US', { maximumFractionDigits: 2 }) : String(Math.round(v * 100) / 100);
  }
  return String(v);
}

export function EditableGrid<T extends { id: string }>(props: Props<T>): React.JSX.Element {
  const { columns, rows, computedFor, onChange, onAdd, addLabel, onDetail, detailTitle, testId } = props;
  const [listId] = useState(() => `dl_${Math.random().toString(36).slice(2, 9)}`);

  const update = (id: string, col: GridColumn<T>, raw: string): void => {
    if (!col.set) return;
    onChange(rows.map((r) => (r.id === id ? col.set!(r, raw) : r)));
  };

  const remove = (id: string): void => {
    onChange(rows.filter((r) => r.id !== id));
  };

  return (
    <div data-testid={testId}>
      <div className="overflow-x-auto rounded-lg border border-border-light">
        <table className="w-full border-collapse text-[11px] tabular-nums">
          <thead className="sticky top-0 z-10 bg-surface-secondary/95 backdrop-blur-sm">
            <tr className="border-b border-border">
              <th scope="col" className="w-8 px-1 py-1.5 text-center font-semibold text-content-tertiary">#</th>
              {columns.map((c) => (
                <th
                  key={c.key}
                  scope="col"
                  style={c.width ? { minWidth: c.width } : undefined}
                  className={clsx(
                    'px-1.5 py-1.5 font-semibold whitespace-nowrap',
                    c.align === 'right' && 'text-right',
                    c.align === 'center' && 'text-center',
                    (!c.align || c.align === 'left') && 'text-left',
                    c.kind === 'computed' ? 'text-oe-blue' : 'text-content-secondary',
                  )}
                >
                  {c.header}
                </th>
              ))}
              <th scope="col" className="w-16 px-1 py-1.5" />
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => {
              const c = computedFor(row);
              const hasError = c.errors.length > 0 || !!c.invalid;
              return (
                <tr key={row.id} className="border-b border-border-light last:border-0 hover:bg-surface-secondary/40">
                  <td className="px-1 py-0.5 text-center text-content-tertiary font-mono">{i + 1}</td>
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      className={clsx(
                        'px-0.5 py-0.5',
                        col.align === 'right' && 'text-right',
                        col.align === 'center' && 'text-center',
                      )}
                      title={col.title?.(row) ?? (hasError ? c.errors.join('; ') : undefined)}
                    >
                      {col.kind === 'input' ? (
                        col.input === 'select' ? (
                          <select
                            value={String(col.get(row) ?? '')}
                            onChange={(e) => update(row.id, col, e.target.value)}
                            className="w-full rounded border border-transparent bg-transparent px-1 py-1 text-[11px] hover:border-border-light focus:border-oe-blue focus:outline-none"
                          >
                            {(col.options ?? []).map((o) => (
                              <option key={o} value={o}>{o || '—'}</option>
                            ))}
                          </select>
                        ) : (
                          <input
                            type={col.input === 'number' ? 'number' : 'text'}
                            step={col.step ?? 'any'}
                            value={col.get(row) ?? ''}
                            placeholder={col.placeholder}
                            list={col.suggestions ? `${listId}_${col.key}` : undefined}
                            onChange={(e) => update(row.id, col, e.target.value)}
                            className={clsx(
                              'w-full rounded border border-transparent bg-transparent px-1 py-1 text-[11px] hover:border-border-light focus:border-oe-blue focus:outline-none',
                              col.align === 'right' && 'text-right font-mono',
                              hasError && col.key === 'memberType' && 'bg-red-50 dark:bg-red-900/20',
                            )}
                          />
                        )
                      ) : (
                        <span
                          className={clsx(
                            'block px-1 py-1 font-mono',
                            col.align === 'right' && 'text-right',
                            c.invalid && ['rule', 'schedule'].includes(col.key) && 'text-red-600 font-semibold',
                          )}
                        >
                          {fmtCell(col.compute ? col.compute(c.values, row) : c.values[col.key])}
                        </span>
                      )}
                      {col.suggestions && (
                        <datalist id={`${listId}_${col.key}`}>
                          {col.suggestions.map((s) => (
                            <option key={s} value={s} />
                          ))}
                        </datalist>
                      )}
                    </td>
                  ))}
                  <td className="px-1 py-0.5 whitespace-nowrap text-center">
                    {hasError && (
                      <span className="mr-1 inline-block align-middle text-amber-500" title={c.errors.join('; ')}>
                        <AlertTriangle size={12} />
                      </span>
                    )}
                    {onDetail && (
                      <button
                        type="button"
                        onClick={() => onDetail(row)}
                        title={detailTitle ?? 'Calculation detail'}
                        className="rounded p-1 text-content-tertiary hover:bg-surface-secondary hover:text-oe-blue transition-colors"
                      >
                        <ListOrdered size={13} />
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => remove(row.id)}
                      title="Delete row"
                      className="rounded p-1 text-content-tertiary hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/20 transition-colors"
                    >
                      <Trash2 size={13} />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <button
        type="button"
        onClick={() => onChange([...rows, onAdd()])}
        className="mt-2 inline-flex items-center gap-1.5 rounded-lg border border-dashed border-border px-3 py-1.5 text-[11px] font-medium text-content-secondary hover:border-oe-blue hover:text-oe-blue transition-colors"
      >
        <Plus size={13} /> {addLabel}
      </button>
    </div>
  );
}
