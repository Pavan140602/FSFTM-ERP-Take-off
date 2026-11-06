// DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
import { ChevronsRight, ChevronsLeft } from 'lucide-react';
import type { PointerEvent as ReactPointerEvent, KeyboardEvent as ReactKeyboardEvent } from 'react';

export function CollapsedEdgeTab({
  side,
  testId,
  label,
  reopenLabel,
  onPointerDown,
  onKeyDown,
}: {
  side: 'left' | 'right';
  testId: string;
  label: string;
  reopenLabel: string;
  onPointerDown: (e: ReactPointerEvent<HTMLDivElement>) => void;
  onKeyDown: (e: ReactKeyboardEvent<HTMLDivElement>) => void;
}) {
  const Icon = side === 'left' ? ChevronsRight : ChevronsLeft;
  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label={label}
      title={reopenLabel}
      tabIndex={0}
      data-testid={testId}
      onPointerDown={onPointerDown}
      onKeyDown={onKeyDown}
      className="group relative w-8 shrink-0 cursor-col-resize touch-none select-none self-stretch rounded-md border border-dashed border-border bg-surface-primary/60 transition-colors hover:border-oe-blue hover:bg-oe-blue/5 focus-visible:outline-none focus-visible:border-oe-blue"
    >
      <div
        aria-hidden="true"
        className="absolute inset-0 flex flex-col items-center justify-center gap-2"
      >
        <div className="flex flex-col gap-1">
          <span className="h-1 w-1 rounded-full bg-content-tertiary transition-colors group-hover:bg-oe-blue" />
          <span className="h-1 w-1 rounded-full bg-content-tertiary transition-colors group-hover:bg-oe-blue" />
          <span className="h-1 w-1 rounded-full bg-content-tertiary transition-colors group-hover:bg-oe-blue" />
        </div>
        <div className="rounded-full border border-border bg-surface-elevated p-2 shadow-xs transition-all group-hover:border-oe-blue group-hover:shadow-sm">
          <Icon size={16} className="text-content-tertiary transition-colors group-hover:text-oe-blue" />
        </div>
      </div>
    </div>
  );
}
