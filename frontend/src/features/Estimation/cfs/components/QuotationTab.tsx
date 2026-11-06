// DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
// Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
/**
 * QuotationTab — the workbook's (empty) Quotation sheet, realised: project
 * header inputs plus per-section totals and a grand total rolled up from
 * every tab's engine results.
 */

import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { calcTrussRow } from '../engine/trussCalc';
import { calcWallRow } from '../engine/wallCalc';
import { calcOpeningRow } from '../engine/openingCalc';
import type { CfsState } from '../cfsStorage';
import { fmtCell } from './EditableGrid';

export function QuotationTab({
  state, onChange,
}: {
  state: CfsState;
  onChange: (q: CfsState['quotation']) => void;
}): React.JSX.Element {
  const { t } = useTranslation();

  const sections = useMemo(() => {
    const sum = (vals: Array<number | null | undefined>): number =>
      vals.reduce<number>((a, v) => a + (typeof v === 'number' ? v : 0), 0);
    const floor = state.floorTrusses.map((r) => calcTrussRow(r, 'floor'));
    const roof = state.roofTrusses.map((r) => calcTrussRow(r, 'roof'));
    const walls = state.walls.map((r) => calcWallRow(r));
    const openings = state.openings.map((r) => calcOpeningRow(r, state.schedule));
    return [
      {
        name: t('cfs.tab_floor', { defaultValue: 'Floor Trusses' }),
        rows: floor.length, lnft: sum(floor.map((c) => (typeof c.totalLnft === 'number' ? c.totalLnft : null))),
        wt: sum(floor.map((c) => (typeof c.weightLb === 'number' ? c.weightLb : null))),
        cost: sum(floor.map((c) => (typeof c.totalCost === 'number' ? c.totalCost : null))),
      },
      {
        name: t('cfs.tab_roof', { defaultValue: 'Roof Trusses' }),
        rows: roof.length, lnft: sum(roof.map((c) => (typeof c.totalLnft === 'number' ? c.totalLnft : null))),
        wt: sum(roof.map((c) => (typeof c.weightLb === 'number' ? c.weightLb : null))),
        cost: sum(roof.map((c) => (typeof c.totalCost === 'number' ? c.totalCost : null))),
      },
      {
        name: t('cfs.tab_walls', { defaultValue: 'Wall Studs' }),
        rows: walls.length, lnft: sum(walls.map((c) => (typeof c.studLnft === 'number' ? c.studLnft : null))),
        wt: sum(walls.map((c) => (typeof c.weightLb === 'number' ? c.weightLb : null))),
        cost: sum(walls.map((c) => (typeof c.totalCost === 'number' ? c.totalCost : null))),
      },
      {
        name: t('cfs.tab_openings', { defaultValue: 'Wall Openings' }),
        rows: openings.length, lnft: 0,
        wt: 0,
        cost: sum(openings.map((c) => (typeof c.totalCost === 'number' ? c.totalCost : null))),
      },
    ];
  }, [state, t]);

  const grand = useMemo(
    () => ({
      lnft: sections.reduce((a, s) => a + s.lnft, 0),
      wt: sections.reduce((a, s) => a + s.wt, 0),
      cost: sections.reduce((a, s) => a + s.cost, 0),
    }),
    [sections],
  );

  const q = state.quotation;
  const field = (
    label: string, value: string, set: (v: string) => void, type = 'text',
  ): React.JSX.Element => (
    <label className="block">
      <span className="mb-1 block text-[11px] font-medium text-content-secondary">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(e) => set(e.target.value)}
        className="w-full rounded-lg border border-border-light bg-surface-primary px-2.5 py-1.5 text-xs focus:border-oe-blue focus:outline-none"
      />
    </label>
  );

  return (
    <div className="space-y-4" data-testid="cfs-quotation">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {field(t('cfs.project', { defaultValue: 'Project' }), q.project, (v) => onChange({ ...q, project: v }))}
        {field(t('cfs.client', { defaultValue: 'Client' }), q.client, (v) => onChange({ ...q, client: v }))}
        {field(t('cfs.date', { defaultValue: 'Date' }), q.date, (v) => onChange({ ...q, date: v }), 'date')}
        <label className="block">
          <span className="mb-1 block text-[11px] font-medium text-content-secondary">{t('cfs.notes', { defaultValue: 'Notes' })}</span>
          <input
            value={q.notes}
            onChange={(e) => onChange({ ...q, notes: e.target.value })}
            className="w-full rounded-lg border border-border-light bg-surface-primary px-2.5 py-1.5 text-xs focus:border-oe-blue focus:outline-none"
          />
        </label>
      </div>

      <div className="overflow-hidden rounded-lg border border-border-light">
        <table className="w-full text-[11px] tabular-nums">
          <thead className="bg-surface-secondary/80">
            <tr className="border-b border-border text-left">
              <th scope="col" className="px-3 py-2 font-semibold text-content-secondary">{t('cfs.section', { defaultValue: 'Section' })}</th>
              <th scope="col" className="px-3 py-2 text-right font-semibold text-content-secondary">{t('cfs.rows', { defaultValue: 'Rows' })}</th>
              <th scope="col" className="px-3 py-2 text-right font-semibold text-content-secondary">{t('cfs.lnft', { defaultValue: 'LNFT (ft)' })}</th>
              <th scope="col" className="px-3 py-2 text-right font-semibold text-content-secondary">{t('cfs.weight', { defaultValue: 'Weight (lb)' })}</th>
              <th scope="col" className="px-3 py-2 text-right font-semibold text-content-secondary">{t('cfs.cost', { defaultValue: 'Cost ($)' })}</th>
            </tr>
          </thead>
          <tbody>
            {sections.map((s) => (
              <tr key={s.name} className="border-b border-border-light last:border-0">
                <td className="px-3 py-2 font-medium text-content-primary">{s.name}</td>
                <td className="px-3 py-2 text-right font-mono text-content-tertiary">{s.rows}</td>
                <td className="px-3 py-2 text-right font-mono">{fmtCell(s.lnft)}</td>
                <td className="px-3 py-2 text-right font-mono">{fmtCell(s.wt)}</td>
                <td className="px-3 py-2 text-right font-mono">${fmtCell(s.cost)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot className="bg-surface-secondary/60">
            <tr className="border-t-2 border-border">
              <td className="px-3 py-2 font-semibold text-content-primary">{t('cfs.grand_total', { defaultValue: 'Grand total' })}</td>
              <td />
              <td className="px-3 py-2 text-right font-mono font-semibold">{fmtCell(grand.lnft)}</td>
              <td className="px-3 py-2 text-right font-mono font-semibold">{fmtCell(grand.wt)}</td>
              <td className="px-3 py-2 text-right font-mono font-semibold">${fmtCell(grand.cost)}</td>
            </tr>
          </tfoot>
        </table>
      </div>
      <p className="text-[11px] text-content-tertiary">
        {t('cfs.quote_hint', {
          defaultValue: 'Costs come from the $/ft and $/lb rates you enter per row (the workbook leaves cost columns blank; defaults are taken from the Reference Sheet where the estimator filled prices).',
        })}
      </p>
    </div>
  );
}
