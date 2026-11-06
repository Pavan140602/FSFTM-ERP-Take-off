// OE-DELIVERY: 2026-10-27-cfs-description
// DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
// Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
/**
 * ScheduleTab — the Door & Window Schedule sheet. Identity + RO dims are
 * editable; the framing members (king/jamb/header/sill) auto-calculate.
 */

import { useMemo, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import type { ScheduleRowInput } from '../data/scheduleDefaults';
import { calcScheduleRow } from '../engine/openingCalc';
import type { Cell, ScheduleRowComputed } from '../engine/types';
import { blankScheduleRow, newId } from '../cfsStorage';
import { EditableGrid, type GridColumn } from './EditableGrid';

const toNum = (v: string): number | null => {
  const t = v.trim();
  if (t === '') return null;
  const n = Number(t);
  return Number.isFinite(n) ? n : null;
};

interface KeyedRow {
  id: string;
  row: ScheduleRowInput;
}

export function ScheduleTab({
  rows, onChange,
}: {
  rows: ScheduleRowInput[];
  onChange: (rows: ScheduleRowInput[]) => void;
}): React.JSX.Element {
  const { t } = useTranslation();
  // Stable React keys independent of the editable schedule ID.
  // Keyed by object identity so add/delete keeps surviving rows stable.
  const keyMap = useRef(new Map<ScheduleRowInput, string>());
  const keyed: KeyedRow[] = useMemo(
    () =>
      rows.map((row) => {
        let k = keyMap.current.get(row);
        if (!k) {
          k = newId('sr');
          keyMap.current.set(row, k);
        }
        return { id: k, row };
      }),
    [rows],
  );

  const setKeyed = (next: KeyedRow[]): void => {
    onChange(next.map((k) => k.row));
  };

  const computed = useMemo(() => {
    const map = new Map<string, ScheduleRowComputed>();
    for (const k of keyed) map.set(k.id, calcScheduleRow(k.row));
    return map;
  }, [keyed]);

  const textCol = (
    key: string, header: string, get: (r: ScheduleRowInput) => string | null,
    set: (r: ScheduleRowInput, v: string) => ScheduleRowInput, width = 100,
  ): GridColumn<KeyedRow> => ({
    key, header, kind: 'input', width,
    get: (k) => get(k.row) ?? '', set: (k, v) => ({ ...k, row: set(k.row, v) }),
  });

  const numCol = (
    key: string, header: string, get: (r: ScheduleRowInput) => number | null,
    set: (r: ScheduleRowInput, v: number | null) => ScheduleRowInput, width = 70,
  ): GridColumn<KeyedRow> => ({
    key, header, kind: 'input', input: 'number', width, align: 'right',
    get: (k) => get(k.row), set: (k, v) => ({ ...k, row: set(k.row, toNum(v)) }),
  });

  const calc = (
    key: string, header: string, width = 72, align: 'left' | 'right' | 'center' = 'right',
  ): GridColumn<KeyedRow> => ({
    key, header, kind: 'computed', width, align,
    get: () => null, compute: (vals) => vals[key] as Cell,
  });

  const columns: GridColumn<KeyedRow>[] = [
    textCol('label', t('cfs.description', { defaultValue: 'Description' }), (r) => r.label, (r, v) => ({ ...r, label: v }), 190),
    textCol('sid', t('cfs.sched_id', { defaultValue: 'Sched. ID' }), (r) => r.id, (r, v) => ({ ...r, id: v }), 70),
    {
      key: 'openingType', header: t('cfs.opening_type', { defaultValue: 'Type' }), kind: 'input',
      input: 'select', width: 80, options: ['Door', 'Window'],
      get: (k) => k.row.openingType ?? '', set: (k, v) => ({ ...k, row: { ...k.row, openingType: v } }),
    },
    textCol('cls', t('cfs.class', { defaultValue: 'Class' }), (r) => r.cls, (r, v) => ({ ...r, cls: v }), 90),
    textCol('headerMaterial', t('cfs.hdr_mat', { defaultValue: 'Header Mat.' }), (r) => r.headerMaterial, (r, v) => ({ ...r, headerMaterial: v }), 110),
    numCol('roWidthIn', t('cfs.ro_w_in', { defaultValue: 'RO W (in)' }), (r) => r.roWidthIn, (r, v) => ({ ...r, roWidthIn: v }), 76),
    numCol('roHeightIn', t('cfs.ro_h_in', { defaultValue: 'RO H (in)' }), (r) => r.roHeightIn, (r, v) => ({ ...r, roHeightIn: v }), 76),
    calc('roWidthFt', t('cfs.ro_w', { defaultValue: 'RO W (ft)' }), 64),
    calc('kingStuds', t('cfs.kings', { defaultValue: 'Kings' }), 56),
    calc('jambStuds', t('cfs.jambs', { defaultValue: 'Jambs' }), 56),
    calc('headerLenFt', t('cfs.hdr_len', { defaultValue: 'Hdr Len (ft)' })),
    calc('headerDepthIn', t('cfs.hdr_depth', { defaultValue: 'Hdr D (in)' }), 64),
    calc('sillYN', t('cfs.sill', { defaultValue: 'Sill' }), 48, 'center'),
    calc('sillLenFt', t('cfs.sill_ft', { defaultValue: 'Sill (ft)' }), 64),
    textCol('notes', t('cfs.notes', { defaultValue: 'Notes' }), (r) => r.notes, (r, v) => ({ ...r, notes: v }), 150),
  ];

  return (
    <EditableGrid<KeyedRow>
      testId="cfs-schedule-grid"
      columns={columns}
      rows={keyed}
      onChange={setKeyed}
      onAdd={() => ({ id: newId('sr'), row: blankScheduleRow() })}
      addLabel={t('cfs.add_row', { defaultValue: 'Add row' })}
      computedFor={(k) => {
        const c = computed.get(k.id);
        if (!c) return { values: {}, errors: [] };
        return {
          values: {
            roWidthFt: c.roWidthFt, kingStuds: c.kingStuds, jambStuds: c.jambStuds,
            headerLenFt: c.headerLenFt, headerDepthIn: c.headerDepthIn,
            sillYN: c.sillYN, sillLenFt: c.sillLenFt,
          },
          errors: [],
        };
      }}
    />
  );
}
