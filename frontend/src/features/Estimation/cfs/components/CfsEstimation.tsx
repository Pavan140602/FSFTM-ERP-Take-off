// DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
// Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
/**
 * CfsEstimation — the Cold-Formed Steel estimation workbook, as a native
 * web section inside Estimating → Estimation.
 *
 * Tabs mirror the workbook sheets: Floor Trusses, Roof Trusses,
 * Exterior Wall Studs, Wall Openings, Door & Window Schedule, Quotation.
 * Every auto-calculated column is produced by the engine in
 * ../engine/* (a 1:1 port of the workbook's LET formulas + VBA macros),
 * verified against the workbook's own cached values.
 */

import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import clsx from 'clsx';
import { loadCfs, saveCfs, type CfsState } from '../cfsStorage';
import { TrussTab } from './TrussTab';
import { WallTab } from './WallTab';
import { OpeningTab } from './OpeningTab';
import { ScheduleTab } from './ScheduleTab';
import { QuotationTab } from './QuotationTab';
import { CalcDetailModal } from './CalcDetailModal';

type TabId = 'floor' | 'roof' | 'walls' | 'openings' | 'schedule' | 'quotation';

export function CfsEstimation(): React.JSX.Element {
  const { t } = useTranslation();
  const [state, setState] = useState<CfsState>(() => loadCfs());
  const [tab, setTab] = useState<TabId>('roof');
  const [detail, setDetail] = useState<{ title: string; lines: string[] } | null>(null);

  useEffect(() => {
    saveCfs(state);
  }, [state]);

  const patch = useCallback((p: Partial<CfsState>) => {
    setState((s) => ({ ...s, ...p }));
  }, []);

  const showDetail = useCallback((title: string, lines: string[]) => {
    setDetail({ title, lines });
  }, []);

  const tabs: Array<{ id: TabId; label: string }> = [
    { id: 'floor', label: t('cfs.tab_floor', { defaultValue: 'Floor Trusses' }) },
    { id: 'roof', label: t('cfs.tab_roof', { defaultValue: 'Roof Trusses' }) },
    { id: 'walls', label: t('cfs.tab_walls', { defaultValue: 'Wall Studs' }) },
    { id: 'openings', label: t('cfs.tab_openings', { defaultValue: 'Wall Openings' }) },
    { id: 'schedule', label: t('cfs.tab_schedule', { defaultValue: 'D&W Schedule' }) },
    { id: 'quotation', label: t('cfs.tab_quotation', { defaultValue: 'Quotation' }) },
  ];

  return (
    <div data-testid="cfs-estimation">
      <div className="mb-3 flex flex-wrap gap-1 border-b border-border" role="tablist">
        {tabs.map((tb) => (
          <button
            key={tb.id}
            type="button"
            role="tab"
            aria-selected={tab === tb.id}
            onClick={() => setTab(tb.id)}
            className={clsx(
              '-mb-px border-b-2 px-3 py-2 text-xs font-medium transition-colors',
              tab === tb.id
                ? 'border-oe-blue text-oe-blue'
                : 'border-transparent text-content-tertiary hover:text-content-primary',
            )}
          >
            {tb.label}
          </button>
        ))}
      </div>

      {tab === 'floor' && (
        <TrussTab kind="floor" rows={state.floorTrusses} onChange={(floorTrusses) => patch({ floorTrusses })} onDetail={showDetail} />
      )}
      {tab === 'roof' && (
        <TrussTab kind="roof" rows={state.roofTrusses} onChange={(roofTrusses) => patch({ roofTrusses })} onDetail={showDetail} />
      )}
      {tab === 'walls' && (
        <WallTab rows={state.walls} onChange={(walls) => patch({ walls })} />
      )}
      {tab === 'openings' && (
        <OpeningTab rows={state.openings} onChange={(openings) => patch({ openings })} schedule={state.schedule} />
      )}
      {tab === 'schedule' && (
        <ScheduleTab rows={state.schedule} onChange={(schedule) => patch({ schedule })} />
      )}
      {tab === 'quotation' && (
        <QuotationTab state={state} onChange={(quotation) => patch({ quotation })} />
      )}

      {detail && (
        <CalcDetailModal title={detail.title} lines={detail.lines} onClose={() => setDetail(null)} />
      )}
    </div>
  );
}
