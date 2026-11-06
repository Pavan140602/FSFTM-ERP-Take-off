// DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
// Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
/**
 * Estimation store — quantity estimations exported from PDF takeoff.
 *
 * An "Estimation" is the estimator's quantity schedule: the takeoff
 * measurements (with their custom ledger columns) saved as a named,
 * project-scoped document that lives under Estimating → Estimation in
 * the sidebar, above the Bid Schedule. Persisted in localStorage (v1);
 * the shape is plain JSON so a future backend sync can adopt it as-is.
 */

export interface EstimationMeasurement {
  type: string;
  group: string;
  annotation: string;
  /** Canonical metric value (D-TKC-016), as stored by takeoff. */
  value: number;
  unit: string;
  /** Display label as rendered on the canvas at export time. */
  label: string;
  page: number;
  customFields?: Record<string, string>;
  /** Takeoff measurement id — the sync key for re-export merge. Rows
   *  exported before this field existed can't be matched and are dropped
   *  on the next "update" sync. */
  takeoffId?: string;
}

export interface EstimationEntry {
  id: string;
  name: string;
  projectId?: string | null;
  projectName?: string | null;
  documentName?: string | null;
  createdAt: string;
  source: 'takeoff';
  customColumns: string[];
  measurements: EstimationMeasurement[];
}

const STORAGE_KEY = 'oe.estimations.v1';

export function loadEstimations(): EstimationEntry[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as EstimationEntry[]) : [];
  } catch {
    return [];
  }
}

function persist(all: EstimationEntry[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(all));
  } catch {
    /* ignore */
  }
}

/** Prepend a new estimation (newest first). Returns the stored entry. */
export function saveEstimation(
  entry: Omit<EstimationEntry, 'id' | 'createdAt'>,
): EstimationEntry {
  const full: EstimationEntry = {
    ...entry,
    id: `est_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    createdAt: new Date().toISOString(),
  };
  const all = loadEstimations();
  persist([full, ...all]);
  return full;
}

/** Replace an existing estimation's data (re-export): keeps the id, refreshes
 *  the payload + timestamp. Returns the updated entry, or null if not found. */
export function updateEstimation(
  id: string,
  patch: Omit<EstimationEntry, 'id' | 'createdAt'> & { createdAt?: string },
): EstimationEntry | null {
  const all = loadEstimations();
  const idx = all.findIndex((e) => e.id === id);
  if (idx === -1) return null;
  const updated: EstimationEntry = {
    ...patch,
    id,
    createdAt: patch.createdAt ?? all[idx]!.createdAt,
  };
  all[idx] = updated;
  persist(all);
  return updated;
}

/** Find a takeoff estimation previously exported from the same document. */
export function findEstimationByDocument(documentName: string | null | undefined): EstimationEntry | null {
  if (!documentName) return null;
  return loadEstimations().find((e) => e.source === 'takeoff' && e.documentName === documentName) ?? null;
}

/** Re-export sync preview: how the incoming rows compare to the existing
 *  entry's rows. */
export interface EstimationSyncDiff {
  added: number;
  updated: number;
  removed: number;
}

function sameMeasurementRow(a: EstimationMeasurement, b: EstimationMeasurement): boolean {
  return (
    a.type === b.type &&
    a.group === b.group &&
    a.annotation === b.annotation &&
    a.value === b.value &&
    a.unit === b.unit &&
    a.label === b.label &&
    a.page === b.page &&
    JSON.stringify(a.customFields ?? {}) === JSON.stringify(b.customFields ?? {})
  );
}

/** Compare incoming takeoff rows against an existing estimation's rows. */
export function diffEstimationMeasurements(
  existing: EstimationMeasurement[],
  incoming: EstimationMeasurement[],
): EstimationSyncDiff {
  const existingById = new Map<string, EstimationMeasurement>();
  for (const m of existing) if (m.takeoffId) existingById.set(m.takeoffId, m);
  const incomingIds = new Set<string>();
  let added = 0;
  let updated = 0;
  for (const m of incoming) {
    if (!m.takeoffId) {
      added++;
      continue;
    }
    incomingIds.add(m.takeoffId);
    const old = existingById.get(m.takeoffId);
    if (!old) added++;
    else if (!sameMeasurementRow(old, m)) updated++;
  }
  let removed = 0;
  for (const m of existing) {
    if (!m.takeoffId || !incomingIds.has(m.takeoffId)) removed++;
  }
  return { added, updated, removed };
}

/** Merge incoming takeoff rows into an existing estimation (re-export sync):
 *  matched rows update in place (existing order kept), new rows append,
 *  rows deleted from takeoff are removed. */
export function syncEstimationMeasurements(
  existing: EstimationMeasurement[],
  incoming: EstimationMeasurement[],
): EstimationMeasurement[] {
  const incomingById = new Map<string, EstimationMeasurement>();
  for (const m of incoming) {
    if (m.takeoffId) incomingById.set(m.takeoffId, m);
  }
  const existingIds = new Set(
    existing.map((m) => m.takeoffId).filter((id): id is string => !!id),
  );
  const merged: EstimationMeasurement[] = [];
  for (const m of existing) {
    if (!m.takeoffId) continue; // old-format row, unmatchable → drop on sync
    const updated = incomingById.get(m.takeoffId);
    if (updated) merged.push(updated); // update in place
    // else: deleted from takeoff → drop
  }
  for (const m of incoming) {
    if (!m.takeoffId || !existingIds.has(m.takeoffId)) merged.push(m); // new → append
  }
  return merged;
}

export function deleteEstimation(id: string): void {
  persist(loadEstimations().filter((e) => e.id !== id));
}

/** Sum of canonical values per measurement type (for the totals row). */
export function estimationTotals(
  measurements: EstimationMeasurement[],
): { type: string; total: number; unit: string; count: number }[] {
  const map = new Map<string, { total: number; unit: string; count: number }>();
  for (const m of measurements) {
    const key = `${m.type}||${m.unit}`;
    const cur = map.get(key) ?? { total: 0, unit: m.unit, count: 0 };
    cur.total += m.value;
    cur.count += 1;
    map.set(key, cur);
  }
  return Array.from(map.entries()).map(([key, v]) => ({
    type: key.split('||')[0]!,
    ...v,
  }));
}
