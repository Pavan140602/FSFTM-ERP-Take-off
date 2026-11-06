// OE-DELIVERY: 2026-11-04-framing-layout
/**
 * "Lay out framing" - for sheets where the framing is not drawn (e.g. a gable
 * roof with only the outline): pick the outline (an area markup), the member
 * (a Tool Chest tool or your own Subject / Label), the direction and the
 * spacing, and every member is placed across the outline at that spacing.
 */
import { useMemo, useState } from 'react';
import { X } from 'lucide-react';
import type { ChestItem, ChestSet } from '../data/tool-chest-sets';
import { displayDesignation } from '../data/tool-chest-sets';
import { parseSpacing, type StartAt } from '../data/framing-layout';

export type FramingDirection = 'horizontal' | 'vertical' | 'along-line' | 'across-line' | 'custom';

export interface FramingRequest {
  direction: FramingDirection;
  customDeg: number;
  spacingM: number;
  spacingText: string;
  startAt: StartAt;
  includeEnd: boolean;
  item: ChestItem | null;
  subject: string;
  label: string;
}

interface Props {
  onClose: () => void;
  onCreate: (req: FramingRequest) => void;
  sets: ChestSet[];
  /** Name of the outline the members go across (the selected area). */
  areaName: string | null;
  /** A selected line (ridge / bearing wall) to run along or across. */
  hasLine: boolean;
}

const PREFERRED = ['zs-roof-trusses', 'zs-floor-trusses', 'zs-floor-joists', 'zs-sji', 'zs-hat'];

export function FramingLayoutDialog({ onClose, onCreate, sets, areaName, hasLine }: Props) {
  const usable = useMemo(
    () => [...sets.filter((s) => !s.recent && s.items.length > 0)].sort((a, b) => {
      const ia = PREFERRED.indexOf(a.id);
      const ib = PREFERRED.indexOf(b.id);
      return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
    }),
    [sets],
  );
  const firstItem = usable[0]?.items[0];
  const [pick, setPick] = useState<string>(firstItem ? `${usable[0]!.id}|${firstItem.id}` : 'custom');
  const [subject, setSubject] = useState('Roof Truss');
  const [label, setLabel] = useState('COMMON TRUSS');
  const [direction, setDirection] = useState<FramingDirection>(hasLine ? 'across-line' : 'vertical');
  const [customDeg, setCustomDeg] = useState(45);
  const [spacing, setSpacing] = useState('24"');
  const [startAt, setStartAt] = useState<StartAt>('edge');
  const [includeEnd, setIncludeEnd] = useState(true);
  const spacingM = parseSpacing(spacing);
  const item = pick === 'custom' ? null : (() => {
    const [sid, iid] = pick.split('|');
    return usable.find((s) => s.id === sid)?.items.find((i) => i.id === iid) ?? null;
  })();
  const canCreate = Boolean(areaName) && spacingM != null && spacingM > 0.02 && (item || label.trim() || subject.trim());
  const field = 'h-7 w-full rounded border border-border bg-surface-primary px-2 text-[12px] text-content-primary';

  return (
    <div className="fixed inset-0 z-[85] flex items-center justify-center bg-black/40 p-4" onClick={onClose} data-testid="framing-dialog">
      <div className="w-full max-w-md rounded-lg border border-border bg-surface-elevated p-4 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-bold text-content-primary">Lay out framing</h2>
          <button type="button" onClick={onClose} className="text-content-tertiary hover:text-content-primary" aria-label="Close"><X size={14} /></button>
        </div>
        <p className="mb-3 text-[11px] leading-snug text-content-tertiary">
          For framing that is not drawn: the members are placed across the outline at the spacing you give. Example - gable roof: draw the roof outline with Area, select it (and the ridge line if you want trusses across it), then pick the truss and 24&quot; O.C.
        </p>
        <div className="space-y-2 text-[12px]">
          <div className="rounded border border-border bg-surface-secondary/50 px-2 py-1.5" data-testid="framing-outline">
            <span className="text-content-tertiary">Outline: </span>
            {areaName ? <b className="text-content-primary">{areaName}</b> : <span className="text-semantic-error">select an area markup (the roof / floor outline) first</span>}
          </div>
          <label className="block">
            <span className="mb-0.5 block text-[11px] text-content-tertiary">Member</span>
            <select className={field} value={pick} onChange={(e) => setPick(e.target.value)} data-testid="framing-member">
              {usable.map((s) => (
                <optgroup key={s.id} label={s.name}>
                  {s.items.map((i) => (
                    <option key={i.id} value={`${s.id}|${i.id}`}>{displayDesignation(i.name)}{i.subject ? ` - ${i.subject}` : ''}</option>
                  ))}
                </optgroup>
              ))}
              <option value="custom">My own Subject / Label…</option>
            </select>
          </label>
          {pick === 'custom' && (
            <div className="grid grid-cols-2 gap-2">
              <label className="block"><span className="mb-0.5 block text-[11px] text-content-tertiary">Subject</span><input className={field} value={subject} onChange={(e) => setSubject(e.target.value)} onKeyDown={(e) => e.stopPropagation()} /></label>
              <label className="block"><span className="mb-0.5 block text-[11px] text-content-tertiary">Label</span><input className={field} value={label} onChange={(e) => setLabel(e.target.value)} onKeyDown={(e) => e.stopPropagation()} /></label>
            </div>
          )}
          <label className="block">
            <span className="mb-0.5 block text-[11px] text-content-tertiary">Members run</span>
            <select className={field} value={direction} onChange={(e) => setDirection(e.target.value as FramingDirection)} data-testid="framing-direction">
              <option value="vertical">Vertical on the sheet</option>
              <option value="horizontal">Horizontal on the sheet</option>
              <option value="across-line" disabled={!hasLine}>Across the selected line (e.g. trusses across the ridge)</option>
              <option value="along-line" disabled={!hasLine}>Along the selected line</option>
              <option value="custom">Custom angle</option>
            </select>
          </label>
          {direction === 'custom' && (
            <label className="block"><span className="mb-0.5 block text-[11px] text-content-tertiary">Angle (degrees from horizontal)</span>
              <input type="number" className={field} value={customDeg} onChange={(e) => setCustomDeg(Number(e.target.value) || 0)} onKeyDown={(e) => e.stopPropagation()} />
            </label>
          )}
          <div className="grid grid-cols-2 gap-2">
            <label className="block">
              <span className="mb-0.5 block text-[11px] text-content-tertiary">Spacing (O.C.)</span>
              <input className={field} value={spacing} onChange={(e) => setSpacing(e.target.value)} onKeyDown={(e) => e.stopPropagation()} placeholder={'24" or 2\'-0" or 600mm'} data-testid="framing-spacing" />
              {spacing && spacingM == null && <span className="text-[10px] text-semantic-error">Try 24, 24&quot;, 2&apos;-0&quot; or 600mm</span>}
            </label>
            <label className="block">
              <span className="mb-0.5 block text-[11px] text-content-tertiary">First member</span>
              <select className={field} value={startAt} onChange={(e) => setStartAt(e.target.value as StartAt)}>
                <option value="edge">At the edge</option>
                <option value="half">Half a space in</option>
                <option value="full">One space in</option>
              </select>
            </label>
          </div>
          <label className="flex items-center gap-1.5 text-[11px] text-content-secondary">
            <input type="checkbox" checked={includeEnd} onChange={(e) => setIncludeEnd(e.target.checked)} /> Add a member at the far edge
          </label>
        </div>
        <div className="mt-4 flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded px-3 py-1 text-[12px] text-content-secondary hover:bg-surface-tertiary">Cancel</button>
          <button
            type="button"
            disabled={!canCreate}
            onClick={() => spacingM != null && onCreate({ direction, customDeg, spacingM, spacingText: spacing, startAt, includeEnd, item, subject: subject.trim(), label: label.trim() })}
            className="rounded bg-oe-blue px-3 py-1 text-[12px] font-semibold text-white disabled:opacity-40"
            data-testid="framing-create"
          >
            Lay out members
          </button>
        </div>
      </div>
    </div>
  );
}
