// OE-DELIVERY: 2026-10-27-cfs-description
// DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
// Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
/**
 * OpeningTab — the Wall Openings sheet: each row references a Door &
 * Window Schedule ID and the framing members auto-calculate from it.
 */

import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import type { ScheduleRowInput } from '../data/scheduleDefaults';
import { calcOpeningRow } from '../engine/openingCalc';
import type { Cell, OpeningRowComputed, OpeningRowInput } from '../engine/types';
import { blankOpeningRow } from '../cfsStorage';
import { EditableGrid, fmtCell, type GridColumn } from './EditableGrid';

const toNum = (v: string): number | null => {
  const t = v.trim();
  if (t === '') return null;
  const n = Number(t);
  return Number.isFinite(n) ? n : null;
};

export function OpeningTab({
  rows, onChange, schedule,
}: {
  rows: OpeningRowInput[];
  onChange: (rows: OpeningRowInput[]) => void;
  schedule: ScheduleRowInput[];
}): React.JSX.Element {
  const { t } = useTranslation();
  const schedIds = useMemo(() => schedule.map((s) => s.id), [schedule]);

  const computed = useMemo(() => {
    const map = new Map<string, OpeningRowComputed>();
    for (const r of rows) map.set(r.id, calcOpeningRow(r, schedule));
    return map;
  }, [rows, schedule]);

  const totals = useMemo(() => {
    let tot = 0;
    for (const r of rows) {
      const c = computed.get(r.id);
      if (c && typeof c.totalCost === 'number') tot += c.totalCost;
    }
    return tot;
  }, [rows, computed]);

  const numCol = (
    key: string, header: string, get: (r: OpeningRowInput) => number | null | undefined,
    set: (r: OpeningRowInput, v: number | null) => OpeningRowInput, width = 64,
  ): GridColumn<OpeningRowInput> => ({
    key, header, kind: 'input', input: 'number', width, align: 'right',
    get: (r) => get(r), set: (r, v) => set(r, toNum(v)),
  });

  const calc = (key: string, header: string, width = 72): GridColumn<OpeningRowInput> => ({
    key, header, kind: 'computed', width, align: 'right',
    get: () => null, compute: (vals) => vals[key] as Cell,
  });

  const columns: GridColumn<OpeningRowInput>[] = [
    {
      key: 'description', header: t('cfs.description', { defaultValue: 'Description' }), kind: 'computed',
      width: 150, align: 'left', get: () => null, compute: (vals) => vals['description'] as Cell,
    },
    {
      key: 'level', header: t('cfs.level', { defaultValue: 'Level' }), kind: 'input', width: 80,
      get: (r) => r.level, set: (r, v) => ({ ...r, level: v }),
    },
    {
      key: 'wallType', header: t('cfs.wall_type', { defaultValue: 'Wall Type' }), kind: 'input', width: 100,
      get: (r) => r.wallType, set: (r, v) => ({ ...r, wallType: v }),
    },
    {
      key: 'loadBearing', header: t('cfs.load', { defaultValue: 'Load Bearing' }), kind: 'input',
      input: 'select', width: 110, options: ['Load Bearing', 'Non-Load Bearing'],
      get: (r) => r.loadBearing, set: (r, v) => ({ ...r, loadBearing: v }),
    },
    numCol('studSpacingIn', t('cfs.spacing_in', { defaultValue: 'Spacing (in)' }), (r) => r.studSpacingIn, (r, v) => ({ ...r, studSpacingIn: v })),
    numCol('wallHeightFt', t('cfs.wall_ht', { defaultValue: 'Wall Ht (ft)' }), (r) => r.wallHeightFt, (r, v) => ({ ...r, wallHeightFt: v })),
    {
      key: 'scheduleRef', header: t('cfs.sched_ref', { defaultValue: 'Sched. ID' }), kind: 'input',
      width: 80, suggestions: schedIds,
      get: (r) => r.scheduleRef, set: (r, v) => ({ ...r, scheduleRef: v }),
      title: (r) => computed.get(r.id)?.scheduleError ?? undefined,
    },
    calc('roWidthFt', t('cfs.ro_w', { defaultValue: 'RO W (ft)' }), 64),
    calc('roHeightFt', t('cfs.ro_h', { defaultValue: 'RO H (ft)' }), 64),
    calc('kingStuds', t('cfs.kings', { defaultValue: 'Kings' }), 56),
    calc('kingStudLnft', t('cfs.king_ft', { defaultValue: 'King (ft)' })),
    calc('jambStuds', t('cfs.jambs', { defaultValue: 'Jambs' }), 56),
    calc('jambStudLnft', t('cfs.jamb_ft', { defaultValue: 'Jamb (ft)' })),
    calc('crippleQty', t('cfs.crip_qty', { defaultValue: 'Crip Qty' }), 60),
    calc('crippleLnft', t('cfs.crip_ft', { defaultValue: 'Crip (ft)' })),
    calc('headerLnft', t('cfs.hdr_ft', { defaultValue: 'Hdr (ft)' })),
    {
      key: 'sillLnft', header: t('cfs.sill_ft', { defaultValue: 'Sill (ft)' }), kind: 'computed',
      width: 64, align: 'right', get: () => null, compute: (vals) => vals['sillLnft'] as Cell,
    },
    numCol('materialCost', t('cfs.mat_cost', { defaultValue: 'Mat $' }), (r) => r.materialCost, (r, v) => ({ ...r, materialCost: v }), 70),
    numCol('connectorCost', t('cfs.conn_cost', { defaultValue: 'Conn $' }), (r) => r.connectorCost, (r, v) => ({ ...r, connectorCost: v }), 70),
    calc('totalCost', t('cfs.total_cost', { defaultValue: 'Total $' }), 76),
  ];

  return (
    <div>
      <EditableGrid<OpeningRowInput>
        testId="cfs-opening-grid"
        columns={columns}
        rows={rows}
        onChange={onChange}
        onAdd={blankOpeningRow}
        addLabel={t('cfs.add_row', { defaultValue: 'Add row' })}
        computedFor={(row) => {
          const c = computed.get(row.id);
          if (!c) return { values: {}, errors: [] };
          return {
            values: {
              description: c.description, roWidthFt: c.roWidthFt, roHeightFt: c.roHeightFt,
              kingStuds: c.kingStuds, kingStudLnft: c.kingStudLnft, jambStuds: c.jambStuds,
              jambStudLnft: c.jambStudLnft, crippleQty: c.crippleQty, crippleLnft: c.crippleLnft,
              headerLnft: c.headerLnft, sillLnft: c.sillLnft, totalCost: c.totalCost,
            },
            errors: c.scheduleError ? [c.scheduleError, ...c.errors] : c.errors,
            invalid: c.scheduleError,
          };
        }}
      />
      <div className="mt-2 flex flex-wrap gap-x-6 gap-y-1 rounded-lg bg-surface-secondary/60 px-3 py-2 text-[11px]">
        <span className="text-content-secondary">{t('cfs.totals', { defaultValue: 'Totals' })}:</span>
        <span><b className="font-mono">${fmtCell(totals)}</b> <span className="text-content-tertiary">{t('cfs.total', { defaultValue: 'total' })}</span></span>
      </div>
    </div>
  );
}
