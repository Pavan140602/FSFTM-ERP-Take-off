// OE-DELIVERY: 2026-10-27-cfs-description
// DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
// Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
/**
 * WallTab — the Exterior Wall Studs sheet as an editable grid.
 */

import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { STRAP_MATERIALS, STUD_MATERIALS, TRACK_MATERIALS } from '../data/materials';
import { calcWallRow } from '../engine/wallCalc';
import type { Cell, WallRowComputed, WallRowInput } from '../engine/types';
import { blankWallRow } from '../cfsStorage';
import { EditableGrid, fmtCell, type GridColumn } from './EditableGrid';

const toNum = (v: string): number | null => {
  const t = v.trim();
  if (t === '') return null;
  const n = Number(t);
  return Number.isFinite(n) ? n : null;
};

export function WallTab({
  rows, onChange,
}: {
  rows: WallRowInput[];
  onChange: (rows: WallRowInput[]) => void;
}): React.JSX.Element {
  const { t } = useTranslation();
  const studNames = useMemo(() => STUD_MATERIALS.map((m) => m.name), []);
  const trackNames = useMemo(() => TRACK_MATERIALS.map((m) => m.name), []);
  const strapNames = useMemo(() => STRAP_MATERIALS.map((m) => m.name), []);

  const computed = useMemo(() => {
    const map = new Map<string, WallRowComputed>();
    for (const r of rows) map.set(r.id, calcWallRow(r));
    return map;
  }, [rows]);

  const totals = useMemo(() => {
    let wt = 0; let mat = 0; let tot = 0;
    for (const r of rows) {
      const c = computed.get(r.id);
      if (!c) continue;
      if (typeof c.weightLb === 'number') wt += c.weightLb;
      if (typeof c.materialCost === 'number') mat += c.materialCost;
      if (typeof c.totalCost === 'number') tot += c.totalCost;
    }
    return { wt, mat, tot };
  }, [rows, computed]);

  const numCol = (
    key: string, header: string, get: (r: WallRowInput) => number | null | undefined,
    set: (r: WallRowInput, v: number | null) => WallRowInput, width = 70,
  ): GridColumn<WallRowInput> => ({
    key, header, kind: 'input', input: 'number', width, align: 'right',
    get: (r) => get(r), set: (r, v) => set(r, toNum(v)),
  });

  const columns: GridColumn<WallRowInput>[] = [
    {
      key: 'description', header: t('cfs.description', { defaultValue: 'Description' }), kind: 'input',
      width: 170, align: 'left',
      get: (r) => r.description ?? '', set: (r, v) => ({ ...r, description: v }),
    },
    {
      key: 'supplyType', header: t('cfs.supply', { defaultValue: 'Supply Type' }), kind: 'input',
      input: 'select', width: 130, options: ['', 'Precut Wall Stud', 'Panelized Wall'],
      get: (r) => r.supplyType, set: (r, v) => ({ ...r, supplyType: v }),
    },
    {
      key: 'studMaterial', header: t('cfs.stud_mat', { defaultValue: 'Stud Material' }), kind: 'input',
      width: 110, suggestions: studNames,
      get: (r) => r.studMaterial, set: (r, v) => ({ ...r, studMaterial: v }),
    },
    {
      key: 'trackMaterial', header: t('cfs.track_mat', { defaultValue: 'Track Material' }), kind: 'input',
      width: 110, suggestions: trackNames,
      get: (r) => r.trackMaterial, set: (r, v) => ({ ...r, trackMaterial: v }),
    },
    {
      key: 'bridgingMaterial', header: t('cfs.bridging_mat', { defaultValue: 'Bridging Mat.' }), kind: 'input',
      width: 100, suggestions: strapNames,
      get: (r) => r.bridgingMaterial, set: (r, v) => ({ ...r, bridgingMaterial: v }),
    },
    numCol('wallLengthFt', t('cfs.wall_len', { defaultValue: 'Wall Len (ft)' }), (r) => r.wallLengthFt, (r, v) => ({ ...r, wallLengthFt: v })),
    numCol('wallHeightFt', t('cfs.wall_ht', { defaultValue: 'Wall Ht (ft)' }), (r) => r.wallHeightFt, (r, v) => ({ ...r, wallHeightFt: v })),
    numCol('studSpacingIn', t('cfs.spacing_in', { defaultValue: 'Spacing (in)' }), (r) => r.studSpacingIn, (r, v) => ({ ...r, studSpacingIn: v }), 64),
    numCol('pricePerLb', t('cfs.price_lb', { defaultValue: '$/lb' }), (r) => r.pricePerLb, (r, v) => ({ ...r, pricePerLb: v }), 60),
    numCol('connectorCost', t('cfs.conn_cost', { defaultValue: 'Conn $' }), (r) => r.connectorCost, (r, v) => ({ ...r, connectorCost: v }), 64),
    ...(['studCount', 'trackCount', 'panelCount', 'studLnft', 'trackFt', 'bridgingLnft', 'weightLb', 'materialCost', 'totalCost'] as const).map(
      (k): GridColumn<WallRowInput> => {
        const headers: Record<string, string> = {
          studCount: t('cfs.stud_count', { defaultValue: 'Studs' }),
          trackCount: t('cfs.track_count', { defaultValue: 'Tracks' }),
          panelCount: t('cfs.panel_count', { defaultValue: 'Panels' }),
          studLnft: t('cfs.stud_lnft', { defaultValue: 'Stud (ft)' }),
          trackFt: t('cfs.track_ft', { defaultValue: 'Track (ft)' }),
          bridgingLnft: t('cfs.bridging_ft', { defaultValue: 'Brdg (ft)' }),
          weightLb: t('cfs.weight_lb', { defaultValue: 'Wt (lb)' }),
          materialCost: t('cfs.mat_cost', { defaultValue: 'Mat $' }),
          totalCost: t('cfs.total_cost', { defaultValue: 'Total $' }),
        };
        return {
          key: k, header: headers[k] ?? k, kind: 'computed', width: 72, align: 'right',
          get: () => null, compute: (vals) => vals[k] as Cell,
        };
      },
    ),
  ];

  return (
    <div>
      <EditableGrid<WallRowInput>
        testId="cfs-wall-grid"
        columns={columns}
        rows={rows}
        onChange={onChange}
        onAdd={blankWallRow}
        addLabel={t('cfs.add_row', { defaultValue: 'Add row' })}
        computedFor={(row) => {
          const c = computed.get(row.id);
          if (!c) return { values: {}, errors: [] };
          return {
            values: {
              studCount: c.studCount, trackCount: c.trackCount, panelCount: c.panelCount,
              studLnft: c.studLnft, trackFt: c.trackFt, bridgingLnft: c.bridgingLnft,
              weightLb: c.weightLb, materialCost: c.materialCost, totalCost: c.totalCost,
            },
            errors: c.errors,
          };
        }}
      />
      <div className="mt-2 flex flex-wrap gap-x-6 gap-y-1 rounded-lg bg-surface-secondary/60 px-3 py-2 text-[11px]">
        <span className="text-content-secondary">{t('cfs.totals', { defaultValue: 'Totals' })}:</span>
        <span><b className="font-mono">{fmtCell(totals.wt)}</b> <span className="text-content-tertiary">lb</span></span>
        <span><b className="font-mono">${fmtCell(totals.mat)}</b> <span className="text-content-tertiary">{t('cfs.material', { defaultValue: 'material' })}</span></span>
        <span><b className="font-mono">${fmtCell(totals.tot)}</b> <span className="text-content-tertiary">{t('cfs.total', { defaultValue: 'total' })}</span></span>
      </div>
    </div>
  );
}
