// DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
// Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
/**
 * CalcDetailModal — the VBA ShowCalcDetail popup as a web dialog:
 * the per-member audit trail (V1… Vn, D1… Dn) for one truss row.
 */

import { useEffect } from 'react';
import { X } from 'lucide-react';

export function CalcDetailModal({
  title, lines, onClose,
}: {
  title: string;
  lines: string[];
  onClose: () => void;
}): React.JSX.Element {
  useEffect(() => {
    const onKey = (e: KeyboardEvent): void => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-[90] flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={title}
      data-testid="cfs-calc-detail"
    >
      <div
        className="flex max-h-[85vh] w-full max-w-2xl flex-col overflow-hidden rounded-xl border border-border bg-surface-primary shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
          <h3 className="text-sm font-semibold text-content-primary">{title}</h3>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1 text-content-tertiary hover:bg-surface-secondary hover:text-content-primary transition-colors"
            aria-label="Close"
          >
            <X size={16} />
          </button>
        </div>
        <pre className="overflow-auto whitespace-pre-wrap p-4 font-mono text-[11px] leading-relaxed text-content-secondary">
          {lines.join('\n')}
        </pre>
      </div>
    </div>
  );
}
