// OE-DELIVERY: 2026-10-27-cfs-description
// DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
// Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
/**
 * TrussTab — Floor Trusses / Roof Trusses workbook sheets as an editable
 * grid. Shared by both tabs; `kind` selects the sheet's screw semantics.
 */

import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { TRUSS_MATERIALS } from '../data/materials';
import { TRUSS_RULES } from '../data/ruleTable';
import { calcTrussRow, trussCalcDetail } from '../engine/trussCalc';
import type { Cell, TrussRowComputed, TrussRowInput } from '../engine/types';
import { blankTrussRow } from '../cfsStorage';
import { EditableGrid, fmtCell, type GridColumn } from './EditableGrid';

const toNum = (v: string): number | null => {
  const t = v.trim();
  if (t === '') return null;
  const n = Number(t);
  return Number.isFinite(n) ? n : null;
};

const numCol = <T,>(
  key: string, header: string, get: (r: T) => number | null | undefined,
  set: (r: T, v: number | null) => T, width = 64,
): GridColumn<T> => ({
  key, header, kind: 'input', input: 'number', width, align: 'right',
  get: (r) => get(r), set: (r, v) => set(r, toNum(v)),
});

const calcCol = (
  key: string, header: string, width = 72,
): GridColumn<TrussRowInput> => ({
  key, header, kind: 'computed', width, align: 'right',
  get: () => null,
  compute: (vals) => vals[key] as Cell,
});

export function TrussTab({
  kind, rows, onChange, onDetail,
}: {
  kind: 'floor' | 'roof';
  rows: TrussRowInput[];
  onChange: (rows: TrussRowInput[]) => void;
  onDetail: (title: string, lines: string[]) => void;
}): React.JSX.Element {
  const { t } = useTranslation();
  const isRoof = kind === 'roof';
  const materialNames = useMemo(() => TRUSS_MATERIALS.map((m) => m.name), []);
  const typeNames = useMemo(() => TRUSS_RULES.map((r) => r.type), []);

  const computed = useMemo(() => {
    const map = new Map<string, TrussRowComputed>();
    for (const r of rows) map.set(r.id, calcTrussRow(r, kind));
    return map;
  }, [rows, kind]);

  const totals = useMemo(() => {
    let lnft = 0; let wt = 0; let mat = 0; let tot = 0;
    for (const r of rows) {
      const c = computed.get(r.id);
      if (!c) continue;
      if (typeof c.totalLnft === 'number') lnft += c.totalLnft;
      if (typeof c.weightLb === 'number') wt += c.weightLb;
      if (typeof c.materialCost === 'number') mat += c.materialCost;
      if (typeof c.totalCost === 'number') tot += c.totalCost;
    }
    return { lnft, wt, mat, tot };
  }, [rows, computed]);

  const columns: GridColumn<TrussRowInput>[] = [
    {
      key: 'description', header: t('cfs.description', { defaultValue: 'Description' }), kind: 'input',
      width: 170, align: 'left',
      get: (r) => r.description ?? '', set: (r, v) => ({ ...r, description: v }),
    },
    {
      key: 'memberType', header: t('cfs.type', { defaultValue: 'Member Type' }), kind: 'input',
      width: 130, suggestions: typeNames,
      get: (r) => r.memberType, set: (r, v) => ({ ...r, memberType: v }),
      title: (r) => computed.get(r.id)?.ruleError ?? undefined,
    },
    {
      key: 'material', header: t('cfs.material', { defaultValue: 'Material' }), kind: 'input',
      width: 110, suggestions: materialNames,
      get: (r) => r.material, set: (r, v) => ({ ...r, material: v }),
    },
    numCol('lengthFt', t('cfs.length_ft', { defaultValue: 'Length (ft)' }), (r) => r.lengthFt, (r, v) => ({ ...r, lengthFt: v })),
    numCol('qty', t('cfs.qty', { defaultValue: 'Qty' }), (r) => r.qty, (r, v) => ({ ...r, qty: v }), 52),
    numCol('slope', t('cfs.slope', { defaultValue: 'Slope :12' }), (r) => r.slope, (r, v) => ({ ...r, slope: v }), 60),
    numCol('fasciaFt', t('cfs.fascia_ft', { defaultValue: 'Fascia (ft)' }), (r) => r.fasciaFt, (r, v) => ({ ...r, fasciaFt: v })),
    numCol('panelSpacingFt', t('cfs.panel_ft', { defaultValue: 'Panel (ft)' }), (r) => r.panelSpacingFt, (r, v) => ({ ...r, panelSpacingFt: v })),
    ...(isRoof ? [
      numCol<TrussRowInput>('bcSlope', t('cfs.bc_slope', { defaultValue: 'BC Slope' }), (r) => r.bcSlope, (r, v) => ({ ...r, bcSlope: v }), 60),
      numCol<TrussRowInput>('atticWidthFt', t('cfs.attic_w', { defaultValue: 'Attic W (ft)' }), (r) => r.atticWidthFt, (r, v) => ({ ...r, atticWidthFt: v })),
      numCol<TrussRowInput>('atticHeightFt', t('cfs.attic_h', { defaultValue: 'Attic H (ft)' }), (r) => r.atticHeightFt, (r, v) => ({ ...r, atticHeightFt: v })),
      numCol<TrussRowInput>('flatLengthFt', t('cfs.flat_len', { defaultValue: 'Flat Len (ft)' }), (r) => r.flatLengthFt, (r, v) => ({ ...r, flatLengthFt: v })),
    ] : []),
    numCol('stiffTC', t('cfs.stiff_tc', { defaultValue: 'Stiff TC' }), (r) => r.stiffTC, (r, v) => ({ ...r, stiffTC: v }), 56),
    numCol('stiffBC', t('cfs.stiff_bc', { defaultValue: 'Stiff BC' }), (r) => r.stiffBC, (r, v) => ({ ...r, stiffBC: v }), 56),
    numCol('stiffWeb', t('cfs.stiff_web', { defaultValue: 'Stiff Web' }), (r) => r.stiffWeb, (r, v) => ({ ...r, stiffWeb: v }), 60),
    numCol('pricePerFt', t('cfs.price_ft', { defaultValue: '$/ft' }), (r) => r.pricePerFt, (r, v) => ({ ...r, pricePerFt: v }), 60),
    numCol('connectorCost', t('cfs.conn_cost', { defaultValue: 'Conn $' }), (r) => r.connectorCost, (r, v) => ({ ...r, connectorCost: v }), 64),
    calcCol('panels', t('cfs.panels', { defaultValue: 'Panels' }), 56),
    calcCol('tcLnft', t('cfs.tc', { defaultValue: 'TC (ft)' })),
    calcCol('bcLnft', t('cfs.bc', { defaultValue: 'BC (ft)' })),
    calcCol('vertLnft', t('cfs.vert', { defaultValue: 'Vert (ft)' })),
    calcCol('diagLnft', t('cfs.diag', { defaultValue: 'Diag (ft)' })),
    calcCol('memberLnft', t('cfs.mbr_truss', { defaultValue: 'Mbr/Truss' })),
    calcCol('totalLnft', t('cfs.total_lnft', { defaultValue: 'Total LNFT' }), 80),
    calcCol('weightLb', t('cfs.weight_lb', { defaultValue: 'Wt (lb)' }), 76),
    {
      key: 'screwSpec', header: t('cfs.screw', { defaultValue: 'Screw' }), kind: 'computed', width: 92, align: 'left',
      get: () => null, compute: (vals) => vals['screwSpec'] as Cell,
    },
    calcCol('screwQty', t('cfs.screw_qty', { defaultValue: 'Scr Qty' }), 60),
    calcCol('materialCost', t('cfs.mat_cost', { defaultValue: 'Mat $' }), 76),
    calcCol('totalCost', t('cfs.total_cost', { defaultValue: 'Total $' }), 80),
  ];

  return (
    <div>
      <EditableGrid<TrussRowInput>
        testId={isRoof ? 'cfs-roof-grid' : 'cfs-floor-grid'}
        columns={columns}
        rows={rows}
        onChange={onChange}
        onAdd={blankTrussRow}
        addLabel={t('cfs.add_row', { defaultValue: 'Add row' })}
        onDetail={(row) => onDetail(
          `${row.memberType || '—'} — ${t('cfs.calc_detail', { defaultValue: 'calculation detail' })}`,
          trussCalcDetail(row),
        )}
        detailTitle={t('cfs.calc_detail', { defaultValue: 'Calculation detail' })}
        computedFor={(row) => {
          const c = computed.get(row.id);
          if (!c) return { values: {}, errors: [] };
          return {
            values: {
              panels: c.panels, tcLnft: c.tcLnft, bcLnft: c.bcLnft,
              vertLnft: c.vertLnft, diagLnft: c.diagLnft, memberLnft: c.memberLnft,
              totalLnft: c.totalLnft, weightLb: c.weightLb, screwSpec: c.screwSpec,
              screwQty: c.screwQty, materialCost: c.materialCost, totalCost: c.totalCost,
            },
            errors: c.errors,
            invalid: c.ruleError,
          };
        }}
      />
      <div className="mt-2 flex flex-wrap gap-x-6 gap-y-1 rounded-lg bg-surface-secondary/60 px-3 py-2 text-[11px]">
        <span className="text-content-secondary">{t('cfs.totals', { defaultValue: 'Totals' })}:</span>
        <span><b className="font-mono">{fmtCell(totals.lnft)}</b> <span className="text-content-tertiary">ft</span></span>
        <span><b className="font-mono">{fmtCell(totals.wt)}</b> <span className="text-content-tertiary">lb</span></span>
        <span><b className="font-mono">${fmtCell(totals.mat)}</b> <span className="text-content-tertiary">{t('cfs.material', { defaultValue: 'material' })}</span></span>
        <span><b className="font-mono">${fmtCell(totals.tot)}</b> <span className="text-content-tertiary">{t('cfs.total', { defaultValue: 'total' })}</span></span>
      </div>
    </div>
  );
}
