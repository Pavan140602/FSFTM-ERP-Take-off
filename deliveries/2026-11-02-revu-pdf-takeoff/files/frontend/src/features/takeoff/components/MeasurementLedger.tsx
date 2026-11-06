// OE-DELIVERY: 2026-10-09-ledger-prop-fix
// DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
// Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
/**
 * Measurement Ledger — sortable, filterable table of ALL measurements.
 *
 * Rendered in the right sidebar when the "Ledger" tab is active.  Uses
 * the pure helpers in `lib/takeoff-ledger.ts` for sort/filter/subtotal
 * math so the component itself stays purely presentational.
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import clsx from 'clsx';
import {
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  FileSpreadsheet,
  Filter,
  HelpCircle,
  Link2,
  Plus,
  X,
} from 'lucide-react';
import type { Measurement } from '../lib/takeoff-types';
import {
  emptyFilter,
  filterMeasurements,
  groupSubtotals,
  ledgerToCsv,
  sortMeasurements,
  typeGrandTotals,
  uniqueFilterOptions,
  withOrdinals,
  type GroupSubtotal,
  type LedgerFilter,
  type LedgerSortColumn,
  type SortDirection,
} from '../lib/takeoff-ledger';
import { usePreferencesStore } from '@/stores/usePreferencesStore';
import { convertQuantity } from '../lib/takeoff-display-units';
import { formatCountQuantity, formatQuantity } from '../lib/measurement-format';
import { displayGroupName } from '../lib/group-labels';
import { localizedUnitCode } from '@/shared/lib/unitLabels';
import {
  degreesFromSlopeFactor,
  effectiveQuantity,
  quantityFactor,
  effectiveUnit,
  isWallMeasurement,
  quantityAdjustmentLabel,
  wallOpeningsCount,
} from '../lib/takeoff-quantity';

export interface MeasurementLedgerProps {
  measurements: Measurement[];
  /** Map of group name → hex color, for the row chip. */
  groupColorMap: Readonly<Record<string, string>>;
  /** Called when a row is clicked — parent navigates to the measurement. */
  onRowClick?: (measurement: Measurement) => void;
  /** Current selection, to highlight the matching row. */
  selectedMeasurementId?: string | null;
  /** Multi-selection for bulk export. When provided (with onToggleSelect),
   *  a checkbox column appears; the parent owns the Set of selected ids. */
  selectedIds?: ReadonlySet<string>;
  /** Toggle one row's multi-selection. */
  onToggleSelect?: (id: string) => void;
  /** Toggle select-all / clear over the currently filtered rows. */
  onToggleSelectAll?: () => void;
  /** Per-measurement "Add to BOQ" action. When provided, a trailing
   *  action column appears on measurable rows (distance / polyline /
   *  area / volume / count) so a calibrated measurement can be pushed
   *  into a BOQ position straight from the ledger. */
  onAddToBoq?: (measurement: Measurement) => void;
  /** Bulk "Add all to BOQ" over the currently filtered, linkable rows
   *  (unconfirmed AI suggestions and annotation rows are excluded). */
  onAddAllToBoq?: (measurements: Measurement[]) => void;
  /** Per-measurement "Create RFI" action. When provided, a second trailing
   *  action button appears on linkable rows so an estimator can raise a
   *  request for information tied to the measurement straight from the
   *  ledger. Gated the same way as {@link onAddToBoq}. */
  onCreateRfi?: (measurement: Measurement) => void;
  /** User-defined column names (managed + persisted per document by the
   *  parent). Rendered after the built-in columns; each cell is editable. */
  customColumns?: string[];
  /** Add a user-defined column. */
  onAddCustomColumn?: (name: string) => void;
  /** Delete a user-defined column (and its cell values). */
  onDeleteCustomColumn?: (name: string) => void;
  /** A custom-column cell was edited. */
  onCustomFieldChange?: (id: string, column: string, value: string) => void;
  /** A predefined editable field was edited. */
  onFieldChange?: (id: string, field: 'annotation' | 'group' | 'qty' | 'label' | 'material' | 'subject', value: string) => void;
  /** Bluebeam-style column visibility. Keys of hidden built-in columns. */
  hiddenColumns?: ReadonlySet<string>;
  /** PDF page labels (e.g. "T1.0") indexed by 0-based page; null when unknown. */
  pageLabels?: string[] | null;
  /** Area display unit from the area tool popup (e.g. "sf"). */
  areaUnit?: string;
  /** Length display unit from the area tool popup (e.g. "ft"). */
  lengthUnit?: string;
  /** Formats a quantity exactly as the sheet caption does (the markup's own
   *  units, else the chosen display unit, else the page calibration). Returns
   *  the number and the unit separately. (OE-DELIVERY 2026-11-02-revu-markups-units) */
  formatQuantityCell?: (m: Measurement, kind: 'length' | 'area' | 'volume', metricValue: number) => { num: string; unit: string };
}

/** Measurement types that carry a pushable quantity. Annotation types
 *  (cloud / arrow / text / rectangle / highlight) have no value to send
 *  to a BOQ. Mirrors the backend's measurable-type set. */
const LINKABLE_TYPES: ReadonlySet<string> = new Set([
  'distance',
  'polyline',
  'area',
  'volume',
  'count',
]);

/** A row the BOQ actions apply to: measurable type, human-confirmed. */
function isLinkable(m: Measurement): boolean {
  return LINKABLE_TYPES.has(m.type) && !m.suggested;
}

/** Shorten a PDF page label to just the sheet code (e.g. "G1.0" from
 *  "[2] 010 TBX_V3.0_G1.0 - Green Checklist Sheet-G1.0"). Matches a trailing
 *  discipline code like G1.0 / A2.1 / T1.0; falls back to the full label. */
export function shortPageLabel(label: string | undefined | null, fallback: string): string {
  if (!label) return fallback;
  const m = label.match(/\b([A-Z]{1,3}\d+(?:\.\d+)?)\s*$/);
  return m ? m[1]! : label;
}

/** Convert an area value to the popup's selected area unit.
 *  `value` is in `fromUnit` (e.g. "mm\u00B2"); returns [converted, shortLabel]. */
export function convertAreaTo(value: number, fromUnit: string, toLabel: string): [number, string] {
  const toM2: Record<string, number> = {
    'mm\u00B2': 1e-6, 'mm2': 1e-6, 'cm\u00B2': 1e-4, 'cm2': 1e-4, 'm\u00B2': 1, 'm2': 1, 'km\u00B2': 1e6, 'km2': 1e6,
    'in\u00B2': 0.00064516, 'in2': 0.00064516, 'ft\u00B2': 0.092903, 'ft2': 0.092903,
    'yd\u00B2': 0.836127, 'yd2': 0.836127, 'mi\u00B2': 2589988, 'mi2': 2589988,
  };
  const fromM2: Record<string, [number, string]> = {
    'sq in': [0.00064516, 'sq in'], 'sf': [0.092903, 'sf'], 'sq yd': [0.836127, 'sq yd'],
    'sq mi': [2589988, 'sq mi'], 'sq mm': [1e-6, 'sq mm'], 'sq cm': [1e-4, 'sq cm'],
    'sq m': [1, 'sq m'], 'sq km': [1e6, 'sq km'], 'ac': [4046.86, 'ac'],
    'ha': [10000, 'ha'], 'tsubo (\u5733)': [3.30579, 'tsubo'],
  };
  const m2 = value * (toM2[fromUnit.trim()] ?? 1);
  const [factor, short] = fromM2[toLabel] ?? [0.092903, 'sf'];
  return [m2 / factor, short];
}

/** Convert a length value (in metres) to the popup's selected length unit.
 *  Returns [converted, shortLabel]. */
export function convertLengthTo(valueM: number, toLabel: string): [number, string] {
  const perM: Record<string, [number, string]> = {
    'mm': [1000, 'mm'], 'cm': [100, 'cm'], 'm': [1, 'm'], 'km': [0.001, 'km'],
    'in': [39.3701, 'in'], 'in"': [39.3701, 'in'], 'ft': [3.28084, 'ft'],
    'ft in"': [3.28084, 'ft'], 'yd': [1.09361, 'yd'], 'mi': [0.000621371, 'mi'],
  };
  const [factor, short] = perM[toLabel] ?? [1, 'm'];
  return [valueM * factor, short];
}

/** Column definitions — i18n key, sort key, right-alignment.  Labels
 *  are resolved at render time so the table follows the active locale.
 *  Exported so the Legend panel can derive its columns from the same
 *  source (future ledger columns appear in the legend automatically). */
/** Types whose Length cell follows the length-unit override. */
const LINEAR_KINDS = new Set(['distance', 'polyline', 'perimeter', 'arc']);
/** Markup-only kinds: no measured figure to format. */
const ANNOTATION_KINDS = new Set(['cloud', 'arrow', 'text', 'highlight', 'line', 'polygon', 'ellipse', 'pen', 'callout', 'stamp', 'legend', 'angle']);

export const COLUMNS: {
  key: LedgerSortColumn;
  i18nKey: string;
  fallback: string;
  align: 'left' | 'right';
}[] = [
  { key: 'ordinal', i18nKey: 'takeoff_viewer.col_ordinal', fallback: '#', align: 'right' },
  { key: 'type', i18nKey: 'takeoff_viewer.col_type', fallback: 'Kind', align: 'left' },
  // Revu Markups list: Subject (category) and Label (text on the sheet).
  { key: 'subject', i18nKey: 'takeoff_viewer.col_subject', fallback: 'Subject', align: 'left' },
  { key: 'label', i18nKey: 'takeoff_viewer.col_label', fallback: 'Label', align: 'left' },
  { key: 'material', i18nKey: 'takeoff_viewer.col_material', fallback: 'Material/Profile', align: 'left' },
  { key: 'length', i18nKey: 'takeoff_viewer.col_length', fallback: 'Length', align: 'right' },
  { key: 'qty', i18nKey: 'takeoff_viewer.col_qty', fallback: 'Qty', align: 'right' },
  { key: 'area', i18nKey: 'takeoff_viewer.col_area', fallback: 'Area', align: 'right' },
  { key: 'slope', i18nKey: 'takeoff_viewer.col_slope', fallback: 'Slope', align: 'left' },
  { key: 'unit', i18nKey: 'takeoff_viewer.col_unit', fallback: 'Unit', align: 'left' },
  { key: 'page', i18nKey: 'takeoff_viewer.col_page', fallback: 'Page Label', align: 'left' },
  { key: 'author', i18nKey: 'takeoff_viewer.col_author', fallback: 'Author', align: 'left' },
  { key: 'date', i18nKey: 'takeoff_viewer.col_date', fallback: 'Date', align: 'left' },
  { key: 'group', i18nKey: 'takeoff_viewer.col_group', fallback: 'Group', align: 'left' },
];

/** Inline-editable ledger cell. Click to edit; Enter/blur commits,
 *  Escape cancels. Stops propagation so the row click never fires. */
function EditableCell({
  value,
  onCommit,
  placeholder,
  testId,
  className,
}: {
  value: string;
  onCommit: (v: string) => void;
  placeholder?: string;
  testId?: string;
  className?: string;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  if (!editing) {
return (
  <button
    type="button"
    onClick={(e) => {
      e.stopPropagation();
      setDraft(value);
      setEditing(true);
    }}
    title={placeholder ?? 'Click to edit'}
    data-testid={testId}
    className={clsx(
      'block w-full rounded-sm px-0.5 py-0.5 text-left transition-colors hover:bg-oe-blue/10 hover:outline hover:outline-1 hover:outline-oe-blue/40',
      className,
    )}
  >
    {value || (
      <span className="text-content-quaternary">{placeholder ?? '—'}</span>
    )}
  </button>
);
  }
  return (
<input
  autoFocus
  value={draft}
  onChange={(e) => setDraft(e.target.value)}
  onBlur={() => {
    setEditing(false);
    if (draft !== value) onCommit(draft);
  }}
  onKeyDown={(e) => {
    e.stopPropagation();
    if (e.key === 'Enter') (e.target as HTMLInputElement).blur();
    else if (e.key === 'Escape') {
      setDraft(value);
      setEditing(false);
    }
  }}
  onClick={(e) => e.stopPropagation()}
  data-testid={testId ? `${testId}-input` : undefined}
  className="w-full min-w-[64px] rounded-sm border border-oe-blue bg-surface-elevated px-1 py-0.5 text-[11px] text-content-primary focus:outline-none"
/>
  );
}

export function MeasurementLedger({
  measurements,
  groupColorMap,
  onRowClick,
  selectedMeasurementId,
  selectedIds,
  onToggleSelect,
  onToggleSelectAll,
  onAddToBoq,
  onAddAllToBoq,
  onCreateRfi,
  customColumns = [],
  onAddCustomColumn,
  onDeleteCustomColumn,
  onCustomFieldChange,
  onFieldChange,
  hiddenColumns,
  pageLabels,
  areaUnit = 'sf',
  lengthUnit,
  formatQuantityCell,
}: MeasurementLedgerProps) {
  const { t, i18n } = useTranslation();
  const multiSelect = Boolean(onToggleSelect);
  /** Check if a built-in column key is visible. */
  const isColVisible = (key: string): boolean => !hiddenColumns?.has(key);
  // Display the canonical-metric quantities in the user's preferred system.
  // Storage stays metric (D-TKC-016); this only converts at the view +
  // CSV-export boundary, matching how QuantityDisplay reads the preference.
  const measurementSystem = usePreferencesStore((s) => s.measurementSystem);
  const [sortCol, setSortCol] = useState<LedgerSortColumn>('ordinal');
  const [sortDir, setSortDir] = useState<SortDirection>('asc');
  const [filter, setFilter] = useState<LedgerFilter>(emptyFilter());
  const [showFilters, setShowFilters] = useState(false);
  /** New custom-column name draft (null = the add-column input is hidden). */
  const [newColumnDraft, setNewColumnDraft] = useState<string | null>(null);

  const options = useMemo(() => uniqueFilterOptions(measurements), [measurements]);

  const filtered = useMemo(
() => filterMeasurements(measurements, filter),
[measurements, filter],
  );

  const sorted = useMemo(
() => sortMeasurements(filtered, sortCol, sortDir),
[filtered, sortCol, sortDir],
  );

  const rows = useMemo(() => withOrdinals(sorted), [sorted]);
  const footers = useMemo(() => typeGrandTotals(sorted), [sorted]);

  /** Rows the bulk "Add all to BOQ" action applies to (respects the
   *  active filters so "add all" means "add everything I'm looking at"). */
  const linkableRows = useMemo(() => sorted.filter(isLinkable), [sorted]);
  const hasActionColumn = Boolean(onAddToBoq) || Boolean(onCreateRfi);
  const columnCount =
COLUMNS.length + customColumns.length + (hasActionColumn ? 1 : 0) + (multiSelect ? 1 : 0);
  /** Select-all checkbox state over the currently filtered rows. */
  const allFilteredSelected =
multiSelect && rows.length > 0 && rows.every((r) => selectedIds?.has(r.measurement.id));

  // Build a grouped structure so we can slot subtotal rows between groups.
  const rowsByGroup = useMemo(() => {
const map = new Map<string, typeof rows>();
for (const row of rows) {
  const g = row.measurement.group || 'General';
  if (!map.has(g)) map.set(g, []);
  map.get(g)!.push(row);
}
return Array.from(map.entries());
  }, [rows]);

  const subtotals = useMemo(() => groupSubtotals(sorted), [sorted]);
  const subtotalByGroup = useMemo(() => {
const map = new Map<string, typeof subtotals[number]>();
for (const s of subtotals) map.set(s.group, s);
return map;
  }, [subtotals]);

  /* ── Scroll the selected row into view + brief flash ──────────────────
   * Triggered when ``selectedMeasurementId`` changes from outside (e.g.
   * the /markups deep-link or programmatic selection from the viewer
   * canvas). The flash class is removed after the CSS animation has had
   * time to play so a subsequent re-select on the same row re-runs it. */
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
if (!selectedMeasurementId) return;
const container = scrollContainerRef.current;
if (!container) return;
const row = container.querySelector<HTMLTableRowElement>(
  `tr[data-measurement-id="${CSS.escape(selectedMeasurementId)}"]`,
);
if (!row) return;
row.scrollIntoView({ behavior: 'smooth', block: 'center' });
row.classList.add('ledger-row-flash');
const timer = window.setTimeout(() => {
  row.classList.remove('ledger-row-flash');
}, 1600);
return () => window.clearTimeout(timer);
  }, [selectedMeasurementId, rows]);

  const toggleSort = (col: LedgerSortColumn) => {
if (sortCol === col) {
  setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
} else {
  setSortCol(col);
  setSortDir('asc');
}
  };

  const toggleInSet = <T,>(set: Set<T>, value: T): Set<T> => {
const next = new Set(set);
if (next.has(value)) next.delete(value);
else next.add(value);
return next;
  };

  const clearFilters = () =>
setFilter({ groups: new Set(), types: new Set(), pages: new Set() });

  const hasFilters =
filter.groups.size > 0 || filter.types.size > 0 || filter.pages.size > 0;

  const handleExport = () => {
const csv = ledgerToCsv(sorted, measurementSystem);
const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
const url = URL.createObjectURL(blob);
const link = document.createElement('a');
link.href = url;
link.download = `takeoff-ledger-${new Date().toISOString().slice(0, 10)}.csv`;
link.click();
URL.revokeObjectURL(url);
  };

  return (
<div
  className="rounded-md border border-border/80 bg-surface-primary/80 backdrop-blur-sm p-3 shadow-sm"
  data-testid="measurement-ledger"
>
  <div className="flex items-center justify-between mb-2 gap-2">
    <p className="text-xs font-semibold text-content-primary">
      {t('takeoff_viewer.ledger', { defaultValue: 'Ledger' })}{' '}
      <span className="text-content-tertiary tabular-nums">
        ({rows.length}/{measurements.length})
      </span>
    </p>
    <div className="flex items-center gap-1">
      <button
        type="button"
        onClick={() => setShowFilters((v) => !v)}
        className={clsx(
          'flex items-center gap-1 px-1.5 py-1 rounded text-[10px] transition-colors',
          showFilters || hasFilters
            ? 'bg-oe-blue/10 text-oe-blue border border-oe-blue/30'
            : 'hover:bg-surface-secondary text-content-tertiary border border-transparent',
        )}
        aria-pressed={showFilters}
        data-testid="ledger-filter-toggle"
      >
        <Filter size={10} />
        {t('takeoff_viewer.filters', { defaultValue: 'Filters' })}
        {hasFilters && (
          <span className="ml-0.5 h-1.5 w-1.5 rounded-full bg-oe-blue" />
        )}
      </button>
      {onAddCustomColumn && (
        newColumnDraft === null ? (
          <button
            type="button"
            onClick={() => setNewColumnDraft('')}
            className="flex items-center gap-1 px-1.5 py-1 rounded text-[10px] hover:bg-surface-secondary text-content-tertiary border border-transparent transition-colors"
            title={t('takeoff_viewer.ledger_add_column_hint', {
              defaultValue: 'Add your own column to the ledger',
            })}
            data-testid="ledger-add-column"
          >
            <Plus size={10} />
            {t('takeoff_viewer.ledger_add_column', { defaultValue: 'Column' })}
          </button>
        ) : (
          <input
            autoFocus
            value={newColumnDraft}
            onChange={(e) => setNewColumnDraft(e.target.value)}
            onBlur={() => setNewColumnDraft(null)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                const name = newColumnDraft.trim();
                if (name && !customColumns.includes(name)) onAddCustomColumn(name);
                setNewColumnDraft(null);
              } else if (e.key === 'Escape') {
                setNewColumnDraft(null);
              }
            }}
            placeholder={t('takeoff_viewer.ledger_column_name', {
              defaultValue: 'Column name…',
            })}
            data-testid="ledger-add-column-input"
            className="w-28 rounded-sm border border-oe-blue bg-surface-elevated px-1.5 py-1 text-[10px] text-content-primary focus:outline-none"
          />
        )
      )}
      <button
        type="button"
        onClick={handleExport}
        disabled={rows.length === 0}
        className="flex items-center gap-1 px-1.5 py-1 rounded text-[10px] hover:bg-surface-secondary text-content-tertiary disabled:opacity-40 disabled:pointer-events-none transition-colors"
        title={t('takeoff_viewer.export_filtered_csv', {
          defaultValue: 'Export filtered view as CSV',
        })}
        data-testid="ledger-export-csv"
      >
        <FileSpreadsheet size={10} />
        CSV
      </button>
      {onAddAllToBoq && (
        <button
          type="button"
          onClick={() => onAddAllToBoq(linkableRows)}
          disabled={linkableRows.length === 0}
          className="flex items-center gap-1 px-1.5 py-1 rounded text-[10px] bg-oe-blue/10 text-oe-blue border border-oe-blue/30 hover:bg-oe-blue/20 disabled:opacity-40 disabled:pointer-events-none transition-colors"
          title={t('takeoff_viewer.ledger_add_all_to_boq_hint', {
            defaultValue:
              'Send every filtered measurement to a BOQ as new positions',
          })}
          data-testid="ledger-add-all-to-boq"
        >
          <Link2 size={10} />
          {t('takeoff_viewer.ledger_add_all_to_boq', {
            defaultValue: 'Add to BOQ',
          })}{' '}
          ({linkableRows.length})
        </button>
      )}
    </div>
  </div>

  {showFilters && (
    <div
      className="mb-2 rounded border border-border-light bg-surface-secondary/50 p-2 space-y-1.5"
      data-testid="ledger-filters"
    >
      <FilterChipGroup
        label={t('takeoff_viewer.filter_groups', { defaultValue: 'Groups' })}
        options={options.groups}
        active={filter.groups}
        onToggle={(v) =>
          setFilter((f) => ({ ...f, groups: toggleInSet(f.groups, v) }))
        }
        renderLabel={(g) => g}
        dataTestId="filter-group"
      />
      <FilterChipGroup
        label={t('takeoff_viewer.filter_types', { defaultValue: 'Types' })}
        options={options.types}
        active={filter.types}
        onToggle={(v) =>
          setFilter((f) => ({ ...f, types: toggleInSet(f.types, v) }))
        }
        renderLabel={(tp) => tp}
        dataTestId="filter-type"
      />
      <FilterChipGroup
        label={t('takeoff_viewer.filter_pages', { defaultValue: 'Pages' })}
        options={options.pages}
        active={filter.pages}
        onToggle={(v) =>
          setFilter((f) => ({ ...f, pages: toggleInSet(f.pages, v) }))
        }
        renderLabel={(p) => `p${p}`}
        dataTestId="filter-page"
      />
      {hasFilters && (
        <button
          type="button"
          onClick={clearFilters}
          className="flex items-center gap-1 text-[10px] text-content-tertiary hover:text-content-primary transition-colors"
        >
          <X size={9} />
          {t('takeoff_viewer.clear_filters', { defaultValue: 'Clear filters' })}
        </button>
      )}
    </div>
  )}

  {measurements.length === 0 ? (
    <p
      className="text-xs text-content-tertiary py-6 text-center"
      data-testid="ledger-empty"
    >
      {t('takeoff_viewer.ledger_empty', {
        defaultValue: 'No measurements yet - pick a tool to start.',
      })}
    </p>
  ) : (
    <div ref={scrollContainerRef} className="max-h-[500px] overflow-auto">
      <table
        className="w-full text-[11px] tabular-nums"
        data-testid="ledger-table"
      >
        <thead className="sticky top-0 bg-surface-primary/95 backdrop-blur-sm z-10">
          <tr className="border-b border-border">
            {multiSelect && (
              <th scope="col" className="w-7 px-1 py-1 text-center" data-testid="ledger-header-select">
                <input
                  type="checkbox"
                  checked={Boolean(allFilteredSelected)}
                  onChange={() => onToggleSelectAll?.()}
                  aria-label={t('takeoff_viewer.ledger_select_all', { defaultValue: 'Select all measurements' })}
                  className="h-3.5 w-3.5 accent-oe-blue align-middle"
                />
              </th>
            )}
            {COLUMNS.map((col) => {
              const isActive = sortCol === col.key;
              const Arrow =
                isActive && sortDir === 'asc'
                  ? ArrowUp
                  : isActive && sortDir === 'desc'
                    ? ArrowDown
                    : ArrowUpDown;
              const label = t(col.i18nKey, { defaultValue: col.fallback });
              return (
                <th
                  key={col.key}
                  onClick={() => toggleSort(col.key)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      toggleSort(col.key);
                    }
                  }}
                  tabIndex={0}
                  role="columnheader"
                  scope="col"
                  aria-sort={
                    isActive
                      ? sortDir === 'asc'
                        ? 'ascending'
                        : 'descending'
                      : 'none'
                  }
                  className={clsx(
                    'px-1.5 py-1 font-semibold text-content-secondary cursor-pointer select-none hover:bg-surface-secondary transition-colors',
                    'focus:outline-none focus-visible:ring-2 focus-visible:ring-oe-blue/40 focus-visible:ring-inset',
                    col.align === 'right' ? 'text-right' : 'text-left',
                  )}
                  data-testid={`ledger-header-${col.key}`}
                  data-sort={isActive ? sortDir : undefined}
                  style={isColVisible(col.key) ? undefined : { display: 'none' }}
                >
                  <span className="inline-flex items-center gap-0.5">
                    {label}
                    <Arrow
                      size={9}
                      aria-hidden
                      className={clsx(
                        'shrink-0',
                        isActive ? 'text-oe-blue' : 'text-content-quaternary',
                      )}
                    />
                  </span>
                </th>
              );
            })}
            {customColumns.map((col) => {
              const isActive = sortCol === col;
              const SortIcon =
                isActive && sortDir === 'asc'
                  ? ArrowUp
                  : isActive && sortDir === 'desc'
                    ? ArrowDown
                    : ArrowUpDown;
              return (
                <th
                  key={`custom-${col}`}
                  scope="col"
                  onClick={() => toggleSort(col)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      toggleSort(col);
                    }
                  }}
                  tabIndex={0}
                  className="px-1.5 py-1 font-semibold text-content-secondary text-left cursor-pointer select-none"
                  data-testid={`ledger-header-custom-${col}`}
                >
                  <span className="inline-flex items-center gap-0.5">
                    {col}
                    <SortIcon
                      size={9}
                      className={clsx(
                        'shrink-0',
                        isActive ? 'text-oe-blue' : 'text-content-quaternary',
                      )}
                    />
                    {onDeleteCustomColumn && (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onDeleteCustomColumn(col);
                        }}
                        title={t('takeoff_viewer.ledger_delete_column', {
                          defaultValue: 'Delete column',
                        })}
                        aria-label={t('takeoff_viewer.ledger_delete_column_named', {
                          defaultValue: 'Delete column {{name}}',
                          name: col,
                        })}
                        data-testid={`ledger-delete-column-${col}`}
                        className="rounded-sm p-0.5 text-content-quaternary opacity-60 transition-all hover:bg-red-100 hover:text-red-600 hover:opacity-100"
                      >
                        <X size={9} />
                      </button>
                    )}
                  </span>
                </th>
              );
            })}
            {hasActionColumn && (
              <th
                scope="col"
                className="px-1.5 py-1 font-semibold text-content-secondary text-right"
                aria-label={t('takeoff_viewer.col_actions', {
                  defaultValue: 'Actions',
                })}
                data-testid="ledger-header-actions"
              />
            )}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 && (
            <tr>
              <td
                colSpan={columnCount}
                className="text-center text-content-tertiary py-4"
                data-testid="ledger-no-matches"
              >
                {t('takeoff_viewer.ledger_no_matches', {
                  defaultValue: 'No measurements match the current filters.',
                })}
              </td>
            </tr>
          )}
          {rowsByGroup.map(([group, groupRows]) => {
            const color = groupColorMap[group] ?? '#3B82F6';
            const sub = subtotalByGroup.get(group);
            return (
              <GroupRows
                key={group}
                group={group}
                groupRows={groupRows}
                color={color}
                subtotal={sub}
                selectedId={selectedMeasurementId ?? null}
                selectedIds={selectedIds}
                onToggleSelect={onToggleSelect}
                onRowClick={onRowClick}
                onAddToBoq={onAddToBoq}
                onCreateRfi={onCreateRfi}
                measurementSystem={measurementSystem}
                customColumns={customColumns}
                onCustomFieldChange={onCustomFieldChange}
                onFieldChange={onFieldChange}
                hiddenColumns={hiddenColumns}
                pageLabels={pageLabels}
                areaUnit={areaUnit}
                lengthUnit={lengthUnit}
                formatQuantityCell={formatQuantityCell}
              />
            );
          })}
        </tbody>
        {footers.length > 0 && (
          <tfoot className="border-t-2 border-border bg-surface-secondary/40">
            {footers.map((gt) => {
              const disp = convertQuantity(gt.total, gt.unit, measurementSystem);
              return (
              <tr
                key={gt.type}
                data-testid="ledger-grand-total"
                data-type={gt.type}
              >
                {multiSelect && <td className="px-1.5 py-1" />}
                <td className="px-1.5 py-1 text-right text-content-tertiary" />
                <td className="px-1.5 py-1 font-semibold text-content-primary capitalize">
                  {t('takeoff_viewer.total_of_type', {
                    defaultValue: 'Total {{type}}',
                    type: gt.type,
                  })}
                </td>
                <td className="px-1.5 py-1 text-content-tertiary">
                  {gt.count} {t('takeoff_viewer.items', { defaultValue: 'items' })}
                </td>
                <td className="px-1.5 py-1" />
                <td className="px-1.5 py-1 text-right font-semibold text-content-primary">
                  {/* Count totals are whole pieces (K-14). */}
                  {gt.type === 'count'
                    ? formatCountQuantity(disp.value)
                    : formatQuantity(disp.value)}
                </td>
                <td className="px-1.5 py-1 text-content-secondary">
                  {localizedUnitCode(disp.unit, i18n.language)}
                </td>
                <td className="px-1.5 py-1" />
                {customColumns.map((col) => (
                  <td key={`custom-total-${col}`} className="px-1.5 py-1" />
                ))}
                {hasActionColumn && <td className="px-1.5 py-1" />}
              </tr>
              );
            })}
          </tfoot>
        )}
      </table>
    </div>
  )}
</div>
  );
}

/** Rows for a single group, followed by subtotal rows (one per unit). */
function GroupRows({
  group,
  groupRows,
  color,
  subtotal,
  selectedId,
  selectedIds,
  onToggleSelect,
  onRowClick,
  onAddToBoq,
  onCreateRfi,
  measurementSystem,
  customColumns,
  onCustomFieldChange,
  onFieldChange,
  hiddenColumns,
  pageLabels,
  areaUnit = 'sf',
  lengthUnit,
  formatQuantityCell,
}: {
  group: string;
  groupRows: { ordinal: number; measurement: Measurement }[];
  color: string;
  subtotal?: GroupSubtotal;
  selectedId: string | null;
  selectedIds?: ReadonlySet<string>;
  onToggleSelect?: (id: string) => void;
  onRowClick?: (m: Measurement) => void;
  onAddToBoq?: (m: Measurement) => void;
  onCreateRfi?: (m: Measurement) => void;
  measurementSystem: import('@/stores/usePreferencesStore').MeasurementSystem;
  customColumns: string[];
  onCustomFieldChange?: (id: string, column: string, value: string) => void;
  onFieldChange?: (id: string, field: 'annotation' | 'group' | 'qty' | 'label' | 'material' | 'subject', value: string) => void;
  hiddenColumns?: ReadonlySet<string>;
  /** PDF page labels (e.g. "T1.0") indexed by 0-based page; null when unknown. */
  pageLabels?: string[] | null;
  /** Area display unit from the area tool popup (e.g. "sf"). */
  areaUnit?: string;
  /** Length display unit from the area tool popup (e.g. "ft"). */
  lengthUnit?: string;
  formatQuantityCell?: (m: Measurement, kind: 'length' | 'area' | 'volume', metricValue: number) => { num: string; unit: string };
}) {
  const { t, i18n } = useTranslation();
  const hasRowActions = Boolean(onAddToBoq) || Boolean(onCreateRfi);
  /** Check if a built-in column key is visible. */
  const isColVisible = (key: string): boolean => !hiddenColumns?.has(key);
  return (
<>
  {groupRows.map(({ ordinal, measurement }) => {
    const selected = selectedId === measurement.id;
    // Reported (effective) quantity: folds slope / wastage / typical-
    // multiplier and the opening-deduction sign, so the row reconciles with
    // the net subtotal below and matches the export.
    const signed = effectiveQuantity(measurement);
    const adjustment = quantityAdjustmentLabel(measurement);
    // Paired with the REPORTED unit: a wall row reads m², not m.
    const disp = convertQuantity(signed, effectiveUnit(measurement) || '', measurementSystem);
    const isWall = isWallMeasurement(measurement);
    const openingCount = isWall ? wallOpeningsCount(measurement) : 0;
    // Same figures and units as the sheet caption (OE-DELIVERY 2026-11-02-revu-markups-units).
    const sheet = (() => {
      if (!formatQuantityCell || measurement.type === 'count' || ANNOTATION_KINDS.has(measurement.type)) return null;
      const sign = signed < 0 ? '-' : '';
      const fmt = (kind: 'length' | 'area' | 'volume', v: number) => {
        const r = formatQuantityCell(measurement, kind, Math.abs(v));
        return { num: sign && Math.abs(v) > 0 ? `${sign}${r.num}` : r.num, unit: r.unit };
      };
      const trueArea = (measurement.value || 0) * quantityFactor(measurement);
      if (measurement.type === 'area' || measurement.type === 'rectangle') {
        const a = fmt('area', signed < 0 ? -trueArea : trueArea);
        return { primary: a, area: a };
      }
      if (measurement.type === 'volume') return { primary: fmt('volume', signed), area: null };
      if (isWall) {
        // A wall: Length column is its run, Area column its (net) wall area.
        return { primary: fmt('length', measurement.value || 0), area: fmt('area', signed) };
      }
      return { primary: fmt('length', signed), area: null };
    })();
    return (
      <tr
        key={measurement.id}
        onClick={() => onRowClick?.(measurement)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            onRowClick?.(measurement);
          }
        }}
        tabIndex={0}
        role="row"
        aria-selected={selected}
        className={clsx(
          'border-b border-border-light cursor-pointer transition-colors',
          'focus:outline-none focus-visible:ring-2 focus-visible:ring-oe-blue/40 focus-visible:ring-inset',
          selected ? 'bg-oe-blue/10' : 'hover:bg-surface-secondary/60',
        )}
        data-testid="ledger-row"
        data-measurement-id={measurement.id}
        data-selected={selected}
      >
        {onToggleSelect && (
          <td className="px-1 py-1 text-center" onClick={(e) => e.stopPropagation()}>
            <input
              type="checkbox"
              checked={Boolean(selectedIds?.has(measurement.id))}
              onChange={() => onToggleSelect(measurement.id)}
              aria-label={`Select measurement ${ordinal}`}
              data-testid={`ledger-select-${measurement.id}`}
              className="h-3.5 w-3.5 accent-oe-blue align-middle"
            />
          </td>
        )}
        {isColVisible('ordinal') && (
        <td className="px-1.5 py-1 text-right text-content-tertiary font-mono">
          {ordinal}
        </td>
        )}
        {isColVisible('type') && (
        <td className="px-1.5 py-1 capitalize">
          {measurement.type}
          {measurement.isDeduction && (
            <span
              className="ml-1 text-[9px] font-semibold uppercase text-semantic-error"
              data-testid="ledger-deduction-badge"
            >
              {t('takeoff_viewer.deduction', { defaultValue: 'deduction' })}
            </span>
          )}
          {isWall && (
            <span
              className="ml-1 text-[9px] font-semibold uppercase text-oe-blue"
              data-testid="ledger-wall-badge"
              title={t('takeoff_wall.ledger_badge_hint', {
                defaultValue: 'Wall area: length x height, minus openings',
              })}
            >
              {openingCount > 0
                ? t('takeoff_wall.ledger_badge_openings', {
                    defaultValue: 'wall, {{count}} openings',
                    count: openingCount,
                  })
                : t('takeoff_wall.ledger_badge', { defaultValue: 'wall' })}
            </span>
          )}
          {adjustment && (
            <span
              className="ml-1 text-[9px] font-semibold text-oe-blue tabular-nums"
              data-testid="ledger-adjustment-badge"
              title={t('takeoff_viewer.adjustment_hint', {
                defaultValue:
                  'Reported quantity adjusted (slope / wastage / typical multiplier)',
              })}
            >
              {adjustment}
            </span>
          )}
        </td>
        )}
        {isColVisible('subject') && (
        <td
          className="px-1.5 py-1 text-content-primary truncate max-w-[140px]"
          title={measurement.customFields?.Subject || ''}
        >
          {onFieldChange ? (
            <EditableCell
              value={measurement.customFields?.Subject || ''}
              onCommit={(v) => onFieldChange(measurement.id, 'subject', v)}
              placeholder="Add subject…"
              testId={`ledger-subject-${measurement.id}`}
              className="truncate"
            />
          ) : (
            measurement.customFields?.Subject || '—'
          )}
        </td>
        )}
        {isColVisible('label') && (
        <td
          className="px-1.5 py-1 text-content-primary truncate max-w-[140px]"
          title={measurement.annotation || ''}
        >
          {/* Label = the text on the sheet, as in Revu. */}
          {onFieldChange ? (
            <EditableCell
              value={measurement.annotation || ''}
              onCommit={(v) => onFieldChange(measurement.id, 'label', v)}
              placeholder="Add label…"
              testId={`ledger-label-${measurement.id}`}
              className="truncate"
            />
          ) : (
            measurement.annotation || '—'
          )}
        </td>
        )}
        {isColVisible('material') && (
        <td
          className="px-1.5 py-1 text-content-primary truncate max-w-[140px]"
          title={measurement.customFields?.Material || ''}
        >
          {onFieldChange ? (
            <EditableCell
              value={measurement.customFields?.Material || ''}
              onCommit={(v) => onFieldChange(measurement.id, 'material', v)}
              placeholder="Add material…"
              testId={`ledger-material-${measurement.id}`}
              className="truncate"
            />
          ) : (
            measurement.customFields?.Material || '—'
          )}
        </td>
        )}
        {isColVisible('length') && (
        <td
          className={clsx(
            'px-1.5 py-1 text-right font-mono',
            measurement.isDeduction && 'text-semantic-error',
          )}
        >
          {/* Voids display as a negative so the column reconciles with the
              net subtotal below (gross - openings). Value is shown in the
              user's measurement system (stored metric, D-TKC-016), unless the
              area popup's length unit overrides it. Counts are whole pieces,
              never "17,00" (K-14). */}
          {sheet
            ? sheet.primary.num
            : measurement.type === 'count'
            ? formatCountQuantity(disp.value)
            : lengthUnit && measurement.type !== 'count'
              ? (() => {
                  // signed is in canonical metres for linear/area types.
                  const [v] = convertLengthTo(signed, lengthUnit);
                  return formatQuantity(v);
                })()
              : formatQuantity(disp.value)}
        </td>
        )}
        {isColVisible('qty') && (
        <td className="px-1.5 py-1 text-right font-mono text-content-primary">
          {onFieldChange ? (
            <EditableCell
              value={String(measurement.multiplier ?? 1)}
              onCommit={(v) => {
                const n = parseInt(v, 10);
                if (Number.isFinite(n) && n >= 1) onFieldChange(measurement.id, 'qty', String(n));
              }}
              placeholder="1"
              testId={`ledger-qty-${measurement.id}`}
            />
          ) : (
            String(measurement.multiplier ?? 1)
          )}
        </td>
        )}
        {isColVisible('area') && (
        <td className="px-1.5 py-1 text-right font-mono text-content-secondary">
          {sheet
            ? sheet.area
              ? `${sheet.area.num}${sheet.area.unit === 'ft-in' ? '' : ` ${sheet.area.unit}`}`
              : '—'
            : measurement.type === 'area' || measurement.type === 'rectangle'
            ? (() => {
                const trueArea = (measurement.value || 0) * quantityFactor(measurement);
                const [v, u] = convertAreaTo(trueArea, measurement.unit || 'm2', areaUnit);
                return `${formatQuantity(v)} ${u}`;
              })()
            : '—'}
        </td>
        )}
        {isColVisible('slope') && (
        <td className="px-1.5 py-1 text-content-secondary">
          {measurement.slopeFactor != null && measurement.slopeFactor > 1
            ? `${degreesFromSlopeFactor(measurement.slopeFactor).toFixed(1)}°`
            : '—'}
        </td>
        )}
        {isColVisible('unit') && (
        <td className="px-1.5 py-1 text-content-secondary">
          {/* A linear row's Length is shown in the chosen length unit (mm by
              default), so the Unit column must name that unit, not the
              stored metre (OE-DELIVERY 2026-11-02-revu-markups-list). */}
          {sheet
            ? sheet.primary.unit
            : localizedUnitCode(
                lengthUnit && LINEAR_KINDS.has(measurement.type) ? lengthUnit : disp.unit,
                i18n.language,
              )}
        </td>
        )}
        {isColVisible('page') && (
        <td className="px-1.5 py-1 text-left text-content-tertiary whitespace-nowrap">
          {shortPageLabel(pageLabels?.[measurement.page - 1], `p.${measurement.page}`)}
        </td>
        )}
        {isColVisible('author') && (
        <td className="px-1.5 py-1 text-content-secondary truncate max-w-[100px]">
          {measurement.author || '—'}
        </td>
        )}
        {isColVisible('date') && (
        <td className="px-1.5 py-1 text-content-tertiary whitespace-nowrap">
          {measurement.createdAt
            ? new Date(measurement.createdAt).toLocaleDateString()
            : '—'}
        </td>
        )}
        {isColVisible('group') && (
        <td className="px-1.5 py-1">
          {onFieldChange ? (
            <span className="inline-flex items-center gap-1">
              <span
                className="h-2 w-2 rounded-full shrink-0"
                style={{ backgroundColor: color }}
              />
              <EditableCell
                value={group}
                onCommit={(v) => {
                  const name = v.trim();
                  if (name && name !== group) onFieldChange(measurement.id, 'group', name);
                }}
                placeholder="Group…"
                testId={`ledger-group-${measurement.id}`}
              />
            </span>
          ) : (
            <span className="inline-flex items-center gap-1">
              <span
                className="h-2 w-2 rounded-full shrink-0"
                style={{ backgroundColor: color }}
              />
              {displayGroupName(group)}
            </span>
          )}
        </td>
        )}
        {customColumns.map((col) => (
          <td key={`custom-${col}`} className="px-1.5 py-1 text-content-primary max-w-[120px]">
            {onCustomFieldChange ? (
              <EditableCell
                value={measurement.customFields?.[col] ?? ''}
                onCommit={(v) => onCustomFieldChange(measurement.id, col, v)}
                placeholder="—"
                testId={`ledger-custom-${measurement.id}-${col}`}
                className="truncate"
              />
            ) : (
              <span className="truncate block">{measurement.customFields?.[col] ?? '—'}</span>
            )}
          </td>
        ))}
        {hasRowActions && (
          <td className="px-1 py-1 text-end">
            {isLinkable(measurement) && (
              <span className="inline-flex items-center justify-end gap-0.5">
                {onAddToBoq && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onAddToBoq(measurement);
                    }}
                    className={clsx(
                      'p-0.5 rounded transition-colors',
                      measurement.linkedPositionId
                        ? 'text-emerald-600 dark:text-emerald-400 hover:bg-emerald-100 dark:hover:bg-emerald-900/30'
                        : 'text-content-tertiary hover:text-oe-blue hover:bg-oe-blue/10',
                    )}
                    aria-label={t('takeoff_viewer.ledger_add_to_boq', {
                      defaultValue: 'Add to BOQ',
                    })}
                    title={
                      measurement.linkedPositionId
                        ? t('takeoff_viewer.ledger_relink_to_boq', {
                            // "ordinal" is a reserved i18next option
                            // (ordinal plurals) - use posOrdinal.
                            defaultValue:
                              'Linked to {{posOrdinal}} - re-link or unlink',
                            posOrdinal: measurement.linkedPositionOrdinal ?? '',
                          })
                        : t('takeoff_viewer.ledger_add_to_boq_hint', {
                            defaultValue:
                              "Send this measurement's quantity to a BOQ position",
                          })
                    }
                    data-testid="ledger-add-to-boq"
                  >
                    <Link2 size={11} />
                  </button>
                )}
                {onCreateRfi && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onCreateRfi(measurement);
                    }}
                    className="p-0.5 rounded text-content-tertiary hover:text-oe-blue hover:bg-oe-blue/10 transition-colors"
                    aria-label={t('takeoff_crosslink.create_rfi', {
                      defaultValue: 'Create RFI',
                    })}
                    title={t('takeoff_crosslink.create_rfi_hint', {
                      defaultValue: 'Raise an RFI tied to this measurement',
                    })}
                    data-testid="ledger-create-rfi"
                  >
                    <HelpCircle size={11} />
                  </button>
                )}
              </span>
            )}
          </td>
        )}
      </tr>
    );
  })}
  {subtotal && Object.keys(subtotal.totals).length > 0 && (
    <>
      {Object.entries(subtotal.totals).map(([unit, total]) => {
        const disp = convertQuantity(total, unit, measurementSystem);
        const isCount = subtotal.countOnly[unit] === true;
        return (
        <tr
          key={`${group}-subtotal-${unit}`}
          className="bg-surface-secondary/40 border-b border-border-light italic"
          data-testid="ledger-subtotal"
          data-group={group}
          data-unit={disp.unit}
        >
          {onToggleSelect && <td />}
          <td />
          <td className="px-1.5 py-1 text-content-tertiary">
            {t('takeoff_viewer.subtotal', { defaultValue: 'subtotal' })}
          </td>
          <td className="px-1.5 py-1 text-content-secondary">
            {displayGroupName(group)} · {subtotal.count}
          </td>
          <td />
          <td className="px-1.5 py-1 text-right font-semibold text-content-primary">
            {isCount ? formatCountQuantity(disp.value) : formatQuantity(disp.value)}
          </td>
          <td className="px-1.5 py-1 text-content-secondary">
            {localizedUnitCode(disp.unit, i18n.language)}
          </td>
          <td />
          {customColumns.map((col) => (
            <td key={`custom-subtotal-${col}`} />
          ))}
          {hasRowActions && <td />}
        </tr>
        );
      })}
    </>
  )}
</>
  );
}

function FilterChipGroup<T extends string | number>({
  label,
  options,
  active,
  onToggle,
  renderLabel,
  dataTestId,
}: {
  label: string;
  options: T[];
  active: Set<T>;
  onToggle: (value: T) => void;
  renderLabel: (value: T) => string;
  dataTestId: string;
}) {
  if (options.length === 0) return null;
  return (
<div>
  <p className="text-[9px] font-bold uppercase tracking-wider text-content-tertiary mb-0.5">
    {label}
  </p>
  <div className="flex flex-wrap gap-1">
    {options.map((opt) => {
      const on = active.has(opt);
      return (
        <button
          key={String(opt)}
          type="button"
          onClick={() => onToggle(opt)}
          className={clsx(
            'px-1.5 py-0.5 rounded-full text-[10px] border transition-colors',
            on
              ? 'bg-oe-blue/15 text-oe-blue border-oe-blue/30'
              : 'bg-surface-primary text-content-secondary border-border hover:border-oe-blue/40',
          )}
          data-testid={dataTestId}
          data-value={String(opt)}
          data-active={on}
        >
          {renderLabel(opt)}
        </button>
      );
    })}
  </div>
</div>
  );
}

export default MeasurementLedger;
