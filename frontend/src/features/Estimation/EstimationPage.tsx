// DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
// Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
/**
 * Estimation page — quantity estimations exported from PDF takeoff.
 *
 * Lives under Estimating → Estimation in the sidebar, above the Bid
 * Schedule. Each estimation is a named snapshot of takeoff measurements
 * (with the estimator's custom ledger columns), expandable to a full
 * table with per-type totals. Deleting an estimation only removes the
 * snapshot; the takeoff document is untouched.
 */

import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import clsx from 'clsx';
import { Calculator, ChevronDown, ChevronRight, Trash2, Ruler } from 'lucide-react';
import {
  deleteEstimation,
  estimationTotals,
  loadEstimations,
  type EstimationEntry,
} from './storage';
import { CfsEstimation } from './cfs/components/CfsEstimation';

function EstimationCard({
  entry,
  onDelete,
}: {
  entry: EstimationEntry;
  onDelete: (id: string) => void;
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const totals = useMemo(() => estimationTotals(entry.measurements), [entry.measurements]);
  const date = useMemo(() => {
    try {
      return new Date(entry.createdAt).toLocaleString();
    } catch {
      return entry.createdAt;
    }
  }, [entry.createdAt]);

  return (
    <div
      className="rounded-xl border border-border bg-surface-primary shadow-xs"
      data-testid="estimation-card"
      data-estimation-id={entry.id}
    >
      <div className="flex items-center gap-3 p-4">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="rounded-md p-1 text-content-tertiary hover:bg-surface-secondary hover:text-content-primary transition-colors"
          aria-expanded={open}
          aria-label={open ? 'Collapse' : 'Expand'}
          data-testid="estimation-toggle"
        >
          {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        </button>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-content-primary">{entry.name}</p>
          <p className="mt-0.5 truncate text-[11px] text-content-tertiary">
            {entry.projectName ?? t('estimation.no_project', { defaultValue: 'No project' })}
            {entry.documentName ? ` · ${entry.documentName}` : ''} · {date} ·{' '}
            {t('estimation.measurement_count', {
              defaultValue: '{{count}} measurements',
              count: entry.measurements.length,
            })}
          </p>
        </div>
        <button
          type="button"
          onClick={() => onDelete(entry.id)}
          className="rounded-md p-1.5 text-content-tertiary hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/20 transition-colors"
          title={t('estimation.delete', { defaultValue: 'Delete estimation' })}
          aria-label={t('estimation.delete_named', {
            defaultValue: 'Delete estimation {{name}}',
            name: entry.name,
          })}
          data-testid="estimation-delete"
        >
          <Trash2 size={14} />
        </button>
      </div>

      {open && (
        <div className="border-t border-border-light px-4 pb-4 pt-2">
          {entry.measurements.length === 0 ? (
            <p className="py-4 text-center text-xs text-content-tertiary">
              {t('estimation.empty_measurements', { defaultValue: 'No measurements in this estimation.' })}
            </p>
          ) : (
            <div className="max-h-[420px] overflow-auto rounded-lg border border-border-light">
              <table className="w-full text-[11px] tabular-nums" data-testid="estimation-table">
                <thead className="sticky top-0 bg-surface-secondary/95 backdrop-blur-sm z-10">
                  <tr className="border-b border-border">
                    {['#', 'Type', 'Label', 'Group', 'Value', 'Unit', 'Page', ...entry.customColumns].map(
                      (h) => (
                        <th
                          key={h}
                          scope="col"
                          className="px-2 py-1.5 text-left font-semibold text-content-secondary"
                        >
                          {h}
                        </th>
                      ),
                    )}
                  </tr>
                </thead>
                <tbody>
                  {entry.measurements.map((m, i) => (
                    <tr key={i} className="border-b border-border-light last:border-0 hover:bg-surface-secondary/40">
                      <td className="px-2 py-1 text-right text-content-tertiary font-mono">{i + 1}</td>
                      <td className="px-2 py-1 capitalize">{m.type}</td>
                      <td className="px-2 py-1 text-content-primary">{m.annotation || m.label || '—'}</td>
                      <td className="px-2 py-1">{m.group || '—'}</td>
                      <td className="px-2 py-1 text-right font-mono">{m.label || m.value}</td>
                      <td className="px-2 py-1 text-content-secondary">{m.unit}</td>
                      <td className="px-2 py-1 text-right text-content-tertiary">{m.page}</td>
                      {entry.customColumns.map((col) => (
                        <td key={col} className="px-2 py-1 text-content-primary">
                          {m.customFields?.[col] ?? '—'}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
                {totals.length > 0 && (
                  <tfoot className="border-t-2 border-border bg-surface-secondary/40">
                    {totals.map((tot) => (
                      <tr key={`${tot.type}-${tot.unit}`}>
                        <td colSpan={4} className="px-2 py-1 text-right font-semibold text-content-primary capitalize">
                          {t('estimation.total_of_type', {
                            defaultValue: 'Total {{type}}',
                            type: tot.type,
                          })}
                        </td>
                        <td className="px-2 py-1 text-right font-mono font-semibold text-content-primary">
                          {tot.total.toFixed(2)}
                        </td>
                        <td className="px-2 py-1 text-content-secondary">{tot.unit}</td>
                        <td colSpan={1 + entry.customColumns.length} />
                      </tr>
                    ))}
                  </tfoot>
                )}
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function EstimationPage() {
  const { t } = useTranslation();
  const [entries, setEntries] = useState<EstimationEntry[]>(() => loadEstimations());
  const [section, setSection] = useState<'takeoff' | 'cfs'>('cfs');

  const handleDelete = (id: string) => {
    deleteEstimation(id);
    setEntries(loadEstimations());
  };

  return (
    <div className="w-full space-y-4 p-4" data-testid="estimation-page">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-oe-blue/10 text-oe-blue">
          <Calculator size={20} />
        </div>
        <div>
          <h1 className="text-lg font-bold text-content-primary">
            {t('estimation.title', { defaultValue: 'Estimation' })}
          </h1>
          <p className="text-xs text-content-tertiary">
            {t('estimation.subtitle', {
              defaultValue:
                'Quantity estimations exported from PDF takeoff — the step between measuring and the Bid Schedule.',
            })}
          </p>
        </div>
      </div>

      <div className="flex gap-1 border-b border-border" role="tablist" aria-label="Estimation sections">
        <button
          type="button"
          role="tab"
          aria-selected={section === 'cfs'}
          onClick={() => setSection('cfs')}
          className={clsx(
            '-mb-px border-b-2 px-3 py-2 text-xs font-medium transition-colors',
            section === 'cfs'
              ? 'border-oe-blue text-oe-blue'
              : 'border-transparent text-content-tertiary hover:text-content-primary',
          )}
        >
          {t('estimation.cfs', { defaultValue: 'CFS Estimation' })}
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={section === 'takeoff'}
          onClick={() => setSection('takeoff')}
          className={clsx(
            '-mb-px border-b-2 px-3 py-2 text-xs font-medium transition-colors',
            section === 'takeoff'
              ? 'border-oe-blue text-oe-blue'
              : 'border-transparent text-content-tertiary hover:text-content-primary',
          )}
        >
          {t('estimation.takeoff_exports', { defaultValue: 'Takeoff Exports' })}
        </button>
      </div>

      {section === 'cfs' ? (
        <CfsEstimation />
      ) : entries.length === 0 ? (
        <div
          className={clsx(
            'flex flex-col items-center gap-3 rounded-xl border border-dashed border-border',
            'bg-surface-primary px-6 py-16 text-center',
          )}
          data-testid="estimation-empty"
        >
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-surface-secondary text-content-tertiary">
            <Ruler size={22} />
          </div>
          <p className="max-w-md text-sm font-medium text-content-primary">
            {t('estimation.empty_title', { defaultValue: 'No estimations yet' })}
          </p>
          <p className="max-w-md text-xs text-content-tertiary">
            {t('estimation.empty_hint', {
              defaultValue:
                'Open a PDF in Takeoff, measure it, then use “Export to Estimation” in the measurements panel. The snapshot lands here.',
            })}
          </p>
          <Link
            to="/takeoff?tab=measurements"
            className="mt-1 rounded-lg bg-oe-blue px-4 py-2 text-xs font-semibold text-white hover:bg-oe-blue/90 transition-colors"
            data-testid="estimation-go-takeoff"
          >
            {t('estimation.open_takeoff', { defaultValue: 'Open PDF Takeoff' })}
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {entries.map((e) => (
            <EstimationCard key={e.id} entry={e} onDelete={handleDelete} />
          ))}
        </div>
      )}
    </div>
  );
}
