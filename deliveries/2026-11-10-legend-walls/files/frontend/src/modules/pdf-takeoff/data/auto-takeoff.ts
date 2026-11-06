// OE-DELIVERY: 2026-11-02-auto-takeoff
/**
 * Auto Takeoff — turning the server's detected framing items into viewer
 * markups, idempotently.
 *
 * The backend (``takeoff/auto_takeoff.py``) returns items: member lines,
 * joist/truss series lines, CFS wall runs by wall tag, column counts and
 * bay areas, each with a stable ``key``. This module merges them into the
 * measurement list so that running Auto Takeoff again — with or without AI,
 * on one sheet or the whole set — NEVER places a markup twice:
 *
 *  1. An item whose key (or label position) matches an earlier auto markup
 *     updates that markup in place — unless the user edited it (moved,
 *     extended, reshaped), in which case the user's version is kept.
 *  2. An item lying on top of ANY existing markup of the same kind (auto or
 *     drawn by hand) is skipped as a duplicate.
 *  3. Only genuinely new items are added.
 *
 * Optionally, unedited auto markups that the new run no longer finds (in the
 * same pages and categories) are removed, so a more accurate re-run replaces
 * a weaker earlier one instead of stacking on it.
 *
 * Pure module: no React, unit-tested in ``auto-takeoff.test.ts``.
 */

export type AutoCategory = 'beams' | 'columns' | 'joists' | 'trusses' | 'walls' | 'areas' | 'other';

export interface AutoItem {
  key: string;
  category: AutoCategory;
  kind: 'line' | 'count' | 'area';
  designation: string;
  label: string;
  spec: string | null;
  points: [number, number][];
  anchor: [number, number];
  page: number;
  series: string | null;
  index: number | null;
  generated: boolean;
  confidence: number;
  /** rules: tags / framing rules; ai; zoom: the detailed scan; legend: walls drawn like a legend sample. */
  source: 'rules' | 'ai' | 'zoom' | 'legend';
  note?: string | null;
  /** Where the profile / tag text sits on the sheet [x0, y0, x1, y1]. */
  label_rect?: number[] | null;
  /** The same text as a band along its reading direction (4 corners). */
  label_quad?: number[][] | null;
  /** What the member is (Load Bearing Wall, Header, Floor Truss, Beam ...),
   *  read from schedules, notes and the sheet title (OE-DELIVERY 2026-11-03-auto-takeoff-roles). */
  role?: string | null;
  /** Profile resolved from a schedule row (e.g. wall tag W1 -> 600S162-54). */
  profile?: string | null;
  /** Column mark (C1, C2 ...) and where it is printed. */
  mark?: string | null;
  mark_quad?: number[][] | null;
  /** Floor / schedule level the member belongs to ('1ST TO 2ND', '2ND FLOOR',
   *  'ROOF') and the wall height from the schedule, feet
   *  (OE-DELIVERY 2026-11-05-framing-rules). */
  level?: string | null;
  height_ft?: number | null;
  /** Column symbol on the sheet: [long side, short side, angle deg] in
   *  drawing units (OE-DELIVERY 2026-11-07-column-shapes). */
  symbol?: number[] | null;
  /** Stud wall (OE-DELIVERY 2026-11-08-stud-walls): full width (drawing
   *  units and inches), stud spacing (drawing units and inches), studs in
   *  the run, and whether the piece is plain wall or a header area. */
  wall_width?: number | null;
  wall_width_in?: number | null;
  stud_spacing?: number | null;
  stud_spacing_in?: number | null;
  stud_count?: number | null;
  segment?: 'wall' | 'header' | null;
  header?: string | null;
}

/** Provenance stored on a measurement placed by Auto Takeoff. */
export interface AutoTag {
  /** Stable item key from the server. */
  key: string;
  cat: AutoCategory;
  /** Member designation / tag (W12X26, 1200S200-54, SW-4 ...). */
  des: string;
  /** Label position the item was read from (PDF units). */
  a: [number, number];
  /** Series key (joist / truss series) and index within it. */
  series?: string | null;
  idx?: number | null;
  src: 'rules' | 'ai' | 'zoom' | 'legend';
  /** Generated at the spacing (not read from drawn lines). */
  gen?: boolean;
  /** Hash of the points as placed; differs once the user edits geometry. */
  h: string;
  /** Rect of the profile text it was read from, highlighted on the sheet
   *  (OE-DELIVERY 2026-11-02-auto-takeoff-columns). */
  lr?: [number, number, number, number];
  /** The user set the profile by hand (OE-DELIVERY 2026-11-02-auto-takeoff-profile-edit):
   *  re-runs keep it, exactly like a moved or reshaped markup. */
  ud?: boolean;
  /** Text band [[x, y] x4] for the Revu-style highlight (rotated text). */
  lq?: [number, number][];
  /** Member role (OE-DELIVERY 2026-11-03-auto-takeoff-roles). */
  role?: string;
  /** Column mark text and its quad on the sheet. */
  mk?: string;
  mq?: [number, number][];
  /** Column symbol [long side, short side, angle deg] (OE-DELIVERY 2026-11-07-column-shapes). */
  sy?: [number, number, number];
  /** Stud wall: width (units), width in inches, stud spacing (units and
   *  inches), piece kind (OE-DELIVERY 2026-11-08-stud-walls). */
  ww?: number;
  wi?: number;
  sd?: number;
  ss?: number;
  seg?: 'wall' | 'header';
  /** The user picked this markup's colour: re-runs keep it
   *  (OE-DELIVERY 2026-11-09-colours-keys). */
  uc?: boolean;
}

export interface AutoPoint {
  x: number;
  y: number;
}

/** The slice of a measurement this module reads and writes. */
export interface AutoMeasurementLike {
  id: string;
  type: string;
  points: AutoPoint[];
  page: number;
  annotation?: string;
  auto?: AutoTag;
}

export const AUTO_CATEGORIES: { key: AutoCategory; label: string; group: string; color: string }[] = [
  { key: 'beams', label: 'Beams', group: 'Beams', color: '#E11D48' },
  { key: 'columns', label: 'Columns', group: 'Columns', color: '#16A34A' },
  { key: 'joists', label: 'Joists', group: 'Joists', color: '#2563EB' },
  { key: 'trusses', label: 'Trusses', group: 'Trusses', color: '#9333EA' },
  { key: 'walls', label: 'CFS Walls', group: 'CFS Walls', color: '#EA580C' },
  { key: 'areas', label: 'Areas', group: 'Areas', color: '#0891B2' },
  { key: 'other', label: 'Other', group: 'Other Members', color: '#A16207' },
];

/** What Auto Takeoff can take off, the way an estimator thinks of it:
 *  structural steel and cold-formed steel member types. Each maps to the
 *  backend categories it needs and the roles it keeps
 *  (OE-DELIVERY 2026-11-03-auto-takeoff-members). */
export interface MemberType {
  key: string;
  label: string;
  group: 'Structural steel' | 'Cold-formed steel' | 'Other';
  cats: AutoCategory[];
  roles: string[];
  color: string;
}
export const MEMBER_TYPES: MemberType[] = [
  { key: 'column', label: 'Columns', group: 'Structural steel', cats: ['columns'], roles: ['Column'], color: '#7C3AED' },
  { key: 'beam', label: 'Beams', group: 'Structural steel', cats: ['beams'], roles: ['Beam'], color: '#1D4ED8' },
  { key: 'steel-joist', label: 'Joists (SJI K / LH / DLH)', group: 'Structural steel', cats: ['joists'], roles: ['Steel Joist'], color: '#4F46E5' },
  { key: 'deck', label: 'Deck areas (B / composite / form)', group: 'Structural steel', cats: ['areas'], roles: ['Deck'], color: '#65A30D' },
  { key: 'base-plate', label: 'Base plates', group: 'Structural steel', cats: ['other'], roles: ['Base Plate'], color: '#0F766E' },
  { key: 'steel-brace', label: 'Steel braces (BRACE-X)', group: 'Structural steel', cats: ['other'], roles: ['Steel Brace'], color: '#B45309' },
  { key: 'lb-wall', label: 'Load bearing walls', group: 'Cold-formed steel', cats: ['walls'], roles: ['Load Bearing Wall', 'CFS Wall'], color: '#DC2626' },
  { key: 'lb-header', label: 'Load bearing headers', group: 'Cold-formed steel', cats: ['other', 'walls'], roles: ['Load Bearing Header'], color: '#EA580C' },
  { key: 'lb-jamb', label: 'Load bearing jambs', group: 'Cold-formed steel', cats: ['other', 'walls'], roles: ['Load Bearing Jamb'], color: '#9333EA' },
  { key: 'shear-wall', label: 'Shear walls', group: 'Cold-formed steel', cats: ['walls'], roles: ['Shear Wall'], color: '#BE123C' },
  { key: 'strap-wall', label: 'Strap braced walls', group: 'Cold-formed steel', cats: ['walls'], roles: ['Strap Braced Wall'], color: '#9F1239' },
  { key: 'holdown', label: 'Holdowns', group: 'Cold-formed steel', cats: ['other'], roles: ['Holdown'], color: '#7E22CE' },
  { key: 'cfs-beam', label: 'CFS beams (boxed / built-up)', group: 'Cold-formed steel', cats: ['beams'], roles: ['CFS Beam'], color: '#1E40AF' },
  { key: 'nlb-wall', label: 'Non-load bearing walls', group: 'Cold-formed steel', cats: ['walls'], roles: ['Non-Load Bearing Wall'], color: '#16A34A' },
  { key: 'nlb-header', label: 'Non-load bearing headers', group: 'Cold-formed steel', cats: ['other', 'walls'], roles: ['Non-Load Bearing Header'], color: '#F59E0B' },
  { key: 'nlb-jamb', label: 'Non-load bearing jambs', group: 'Cold-formed steel', cats: ['other', 'walls'], roles: ['Non-Load Bearing Jamb'], color: '#C084FC' },
  { key: 'truss', label: 'Trusses (roof / floor)', group: 'Cold-formed steel', cats: ['trusses'], roles: ['Roof Truss', 'Floor Truss'], color: '#92400E' },
  { key: 'cfs-joist', label: 'Joists (CFS)', group: 'Cold-formed steel', cats: ['joists'], roles: ['CFS Joist', 'Floor Joist', 'Roof Joist', 'Ceiling Joist'], color: '#2563EB' },
  { key: 'hat', label: 'Hat channels', group: 'Cold-formed steel', cats: ['joists', 'other'], roles: ['Hat Channel'], color: '#0D9488' },
  { key: 'other', label: 'Other (angles, track, bays)', group: 'Other', cats: ['other', 'areas'], roles: ['Angle', 'Track', 'Stud', 'Other', 'Header', 'Jamb', 'Framing Area'], color: '#A16207' },
];
/** Categories + roles for a set of picked member types. */
/** Member types added with the house framing rules; turned on for anyone
 *  whose saved choices predate them (OE-DELIVERY 2026-11-05-framing-rules). */
export const RULES_MEMBER_TYPES = ['base-plate', 'steel-brace', 'strap-wall', 'holdown', 'cfs-beam'];

export function memberScope(keys: string[]): { cats: AutoCategory[]; roles: Set<string> } {
  const picked = MEMBER_TYPES.filter((t) => keys.includes(t.key));
  return {
    cats: [...new Set(picked.flatMap((t) => t.cats))],
    roles: new Set(picked.flatMap((t) => t.roles)),
  };
}

export function autoCategoryMeta(cat: string) {
  return AUTO_CATEGORIES.find((c) => c.key === cat) ?? AUTO_CATEGORIES[AUTO_CATEGORIES.length - 1]!;
}

/** Revu "Subject" of an auto markup, shown in the Markups list Label
 *  column (OE-DELIVERY 2026-11-02-revu-markups-list). */
export function autoSubject(cat: string): string {
  return (
    {
      beams: 'Beam',
      columns: 'Column',
      joists: 'Joist',
      trusses: 'Truss',
      walls: 'CFS Wall',
      areas: 'Framing Area',
      other: 'Member',
    } as Record<string, string>
  )[cat] ?? 'Member';
}

/** Group name for an item: category + designation, so the ledger totals
 *  each size separately (Beams: W12X26, CFS Walls: SW-4 ...). */
export function autoGroupName(cat: AutoCategory, designation: string): string {
  return `${autoCategoryMeta(cat).group}: ${designation}`;
}

export function pointsHash(points: AutoPoint[]): string {
  return points.map((p) => `${Math.round(p.x * 4)},${Math.round(p.y * 4)}`).join(';');
}

export function isAutoEdited(m: AutoMeasurementLike): boolean {
  return Boolean(m.auto) && (pointsHash(m.points) !== m.auto!.h || Boolean(m.auto!.ud));
}

/** Clean a profile typed by the user: trimmed, single spaces, upper case
 *  ("w12x26" -> "W12X26", "c1  hss8x8x1/2" -> "C1 HSS8X8X1/2"). */
export function normalizeProfile(text: string): string {
  return text.trim().replace(/\s+/g, ' ').toUpperCase().slice(0, 60);
}

export function itemPoints(item: AutoItem): AutoPoint[] {
  return item.points.map(([x, y]) => ({ x, y }));
}

export function tagForItem(item: AutoItem, points: AutoPoint[] = itemPoints(item)): AutoTag {
  return {
    key: item.key,
    cat: item.category,
    des: item.designation,
    a: item.anchor,
    series: item.series,
    idx: item.index,
    src: item.source,
    gen: item.generated || undefined,
    h: pointsHash(points),
    ...(Array.isArray(item.label_rect) && item.label_rect.length === 4
      ? { lr: item.label_rect as [number, number, number, number] }
      : {}),
    ...(Array.isArray(item.label_quad) && item.label_quad.length === 4
      ? { lq: item.label_quad.map((q) => [q[0]!, q[1]!] as [number, number]) }
      : {}),
    ...(item.role ? { role: item.role } : {}),
    ...(item.mark ? { mk: item.mark } : {}),
    ...(Array.isArray(item.mark_quad) && item.mark_quad.length === 4
      ? { mq: item.mark_quad.map((q) => [q[0]!, q[1]!] as [number, number]) }
      : {}),
    ...(Array.isArray(item.symbol) && item.symbol.length === 3
      ? { sy: [item.symbol[0]!, item.symbol[1]!, item.symbol[2]!] as [number, number, number] }
      : {}),
    ...(item.wall_width ? { ww: item.wall_width } : {}),
    ...(item.wall_width_in ? { wi: item.wall_width_in } : {}),
    ...(item.stud_spacing ? { sd: item.stud_spacing } : {}),
    ...(item.stud_spacing_in ? { ss: item.stud_spacing_in } : {}),
    ...(item.segment ? { seg: item.segment } : {}),
  };
}

export function isAutoTag(v: unknown): v is AutoTag {
  if (!v || typeof v !== 'object') return false;
  const t = v as Record<string, unknown>;
  return (
    typeof t.key === 'string' &&
    typeof t.cat === 'string' &&
    typeof t.des === 'string' &&
    typeof t.h === 'string' &&
    Array.isArray(t.a) &&
    t.a.length === 2
  );
}

/* ── geometry ──────────────────────────────────────────────────────── */

const LINE_TYPES = new Set(['distance', 'polyline']);
const AREA_TYPES = new Set(['area', 'rectangle', 'rectArea']);

/** True when two straight lines lie on top of each other (same direction,
 *  same position, overlapping for most of the shorter one). */
export function linesOverlap(a: [AutoPoint, AutoPoint], b: [AutoPoint, AutoPoint], tol = 4): boolean {
  const ax = a[1].x - a[0].x;
  const ay = a[1].y - a[0].y;
  const bx = b[1].x - b[0].x;
  const by = b[1].y - b[0].y;
  const la = Math.hypot(ax, ay);
  const lb = Math.hypot(bx, by);
  if (la < 1e-6 || lb < 1e-6) return false;
  const cos = Math.abs((ax * bx + ay * by) / (la * lb));
  if (cos < Math.cos((5 * Math.PI) / 180)) return false;
  const ux = ax / la;
  const uy = ay / la;
  // Perpendicular distance of b's endpoints from a's line.
  const d0 = Math.abs((b[0].x - a[0].x) * -uy + (b[0].y - a[0].y) * ux);
  const d1 = Math.abs((b[1].x - a[0].x) * -uy + (b[1].y - a[0].y) * ux);
  if (Math.max(d0, d1) > tol) return false;
  const t0 = (b[0].x - a[0].x) * ux + (b[0].y - a[0].y) * uy;
  const t1 = (b[1].x - a[0].x) * ux + (b[1].y - a[0].y) * uy;
  const lo = Math.max(0, Math.min(t0, t1));
  const hi = Math.min(la, Math.max(t0, t1));
  const overlap = hi - lo;
  return overlap >= 0.6 * Math.min(la, lb);
}

function segmentsOf(m: AutoMeasurementLike): [AutoPoint, AutoPoint][] {
  const out: [AutoPoint, AutoPoint][] = [];
  for (let i = 0; i + 1 < m.points.length; i++) out.push([m.points[i]!, m.points[i + 1]!]);
  return out;
}

function bbox(points: AutoPoint[]): [number, number, number, number] {
  let x0 = Infinity;
  let y0 = Infinity;
  let x1 = -Infinity;
  let y1 = -Infinity;
  for (const p of points) {
    x0 = Math.min(x0, p.x);
    y0 = Math.min(y0, p.y);
    x1 = Math.max(x1, p.x);
    y1 = Math.max(y1, p.y);
  }
  return [x0, y0, x1, y1];
}

export function areasOverlap(a: AutoPoint[], b: AutoPoint[]): boolean {
  const A = bbox(a);
  const B = bbox(b);
  const ix = Math.max(0, Math.min(A[2], B[2]) - Math.max(A[0], B[0]));
  const iy = Math.max(0, Math.min(A[3], B[3]) - Math.max(A[1], B[1]));
  const small = Math.min((A[2] - A[0]) * (A[3] - A[1]), (B[2] - B[0]) * (B[3] - B[1]));
  return small > 0 && (ix * iy) / small > 0.6;
}

/* ── merge ─────────────────────────────────────────────────────────── */

export interface MergeOptions {
  /** Pages the run covered (stale clean-up only touches these). */
  pages: Set<number>;
  /** Categories the run covered. */
  categories: Set<string>;
  /** Remove unedited auto markups the run no longer finds. */
  removeStale: boolean;
  /** Member roles the run covered: stale clean-up only touches these
   *  (markups without a role fall back to the category). */
  roles?: Set<string>;
  /** Auto markups the user deleted: a re-run must not place them again
   *  (OE-DELIVERY 2026-11-02-auto-takeoff-list). */
  rejected?: RejectedTag[];
}

/** What is remembered of a deleted auto markup. */
export type RejectedTag = Pick<AutoTag, 'key' | 'cat' | 'des' | 'a' | 'idx'> & { page: number };

export function rejectedFrom(m: AutoMeasurementLike): RejectedTag | null {
  if (!m.auto) return null;
  return { key: m.auto.key, cat: m.auto.cat, des: m.auto.des, a: m.auto.a, idx: m.auto.idx ?? null, page: m.page };
}

export interface MergeSummary {
  added: number;
  updated: number;
  unchanged: number;
  keptEdited: number;
  duplicates: number;
  removed: number;
  /** Count points added to existing column counts. */
  pointsAdded: number;
  /** Items skipped because the user deleted them before. */
  rejected: number;
}

export interface MergeResult<M extends AutoMeasurementLike> {
  next: M[];
  summary: MergeSummary;
}

function sameItem(tag: Pick<AutoTag, 'key' | 'cat' | 'des' | 'a' | 'idx'>, item: AutoItem): boolean {
  if (tag.key === item.key) return true;
  if (tag.cat !== item.category || tag.des !== item.designation) return false;
  if ((tag.idx ?? null) !== (item.index ?? null)) return false;
  // Same label read again, its position nudged across a rounding boundary.
  return Math.hypot(tag.a[0] - item.anchor[0], tag.a[1] - item.anchor[1]) <= 12;
}

/**
 * Merge a run's items into the measurement list.
 *
 * ``build`` turns an item into a NEW measurement (id, style, value);
 * ``update`` re-applies an item to an existing unedited auto measurement
 * (new points / value / label) while keeping its id, server link and the
 * user's style overrides.
 */
export function mergeAutoItems<M extends AutoMeasurementLike>(
  existing: M[],
  items: AutoItem[],
  build: (item: AutoItem) => M,
  update: (m: M, item: AutoItem) => M,
  opts: MergeOptions,
): MergeResult<M> {
  const summary: MergeSummary = { added: 0, updated: 0, unchanged: 0, keptEdited: 0, duplicates: 0, removed: 0, pointsAdded: 0, rejected: 0 };
  const next: M[] = [...existing];
  const matched = new Set<string>();
  const byPage = new Map<number, number[]>();
  const indexOf = (page: number) => {
    let list = byPage.get(page);
    if (!list) {
      list = [];
      next.forEach((m, i) => {
        if (m.page === page) list!.push(i);
      });
      byPage.set(page, list);
    }
    return list;
  };
  const pushNew = (m: M) => {
    next.push(m);
    indexOf(m.page).push(next.length - 1);
    matched.add(m.id);
  };

  for (const item of items) {
    const pts = itemPoints(item);
    const onPage = indexOf(item.page);

    // 1. The same item placed by an earlier run.
    const prevIdx = onPage.find((i) => {
      const m = next[i]!;
      return m.auto ? sameItem(m.auto, item) && !matched.has(m.id) : false;
    });
    if (prevIdx !== undefined) {
      const prev = next[prevIdx]!;
      matched.add(prev.id);
      if (item.kind === 'count') {
        // Columns: add newly found symbols, never re-add ones already there.
        const fresh = pts.filter((p) => !onPage.some((i) => {
          const m = next[i]!;
          return m.type === 'count' && m.points.some((q) => Math.hypot(q.x - p.x, q.y - p.y) <= 6);
        }));
        if (fresh.length === 0) {
          summary.unchanged++;
        } else if (isAutoEdited(prev)) {
          summary.keptEdited++;
        } else {
          const merged: AutoItem = { ...item, points: [...prev.points.map((p) => [p.x, p.y] as [number, number]), ...fresh.map((p) => [p.x, p.y] as [number, number])] };
          next[prevIdx] = update(prev, merged);
          summary.updated++;
          summary.pointsAdded += fresh.length;
        }
        continue;
      }
      if (isAutoEdited(prev)) {
        summary.keptEdited++;
      } else if (
        pointsHash(pts) === prev.auto!.h &&
        prev.annotation === item.label &&
        // Older markups lack the profile-text rect: refresh them once.
        (prev.auto!.lr || !item.label_rect) &&
        (prev.auto!.lq || !item.label_quad)
      ) {
        summary.unchanged++;
      } else {
        next[prevIdx] = update(prev, item);
        summary.updated++;
      }
      continue;
    }

    // 1b. The user deleted this one before: leave it deleted.
    if (opts.rejected?.some((r) => r.page === item.page && sameItem(r, item))) {
      summary.rejected++;
      continue;
    }

    // 2. Something already drawn there (by hand, or another auto markup).
    if (item.kind === 'line') {
      // Every piece of the item: curved members come as polylines
      // (OE-DELIVERY 2026-11-06-zoom-scan).
      const segs = segmentsOf({ points: pts } as AutoMeasurementLike);
      const dupIdx = onPage.find((i) => {
        const m = next[i]!;
        // A shear / strap-braced panel lies on its bearing wall on purpose:
        // walls of another tag on the same line are not copies
        // (OE-DELIVERY 2026-11-08-stud-walls).
        if (item.category === 'walls' && m.auto?.cat === 'walls' && m.auto.des !== item.designation) return false;
        return LINE_TYPES.has(m.type) && segmentsOf(m).some((s) => segs.some((seg) => linesOverlap(s, seg) || linesOverlap(seg, s)));
      });
      if (dupIdx !== undefined) {
        // An auto markup found again under a new key still counts as found.
        matched.add(next[dupIdx]!.id);
        summary.duplicates++;
        continue;
      }
    } else if (item.kind === 'area') {
      const dupIdx = onPage.find((i) => {
        const m = next[i]!;
        return AREA_TYPES.has(m.type) && m.points.length >= 3 && areasOverlap(m.points, pts);
      });
      if (dupIdx !== undefined) {
        matched.add(next[dupIdx]!.id);
        summary.duplicates++;
        continue;
      }
    } else {
      // A column placed earlier without a profile ("COLUMN") that this run
      // can now name: rename it in place instead of skipping it.
      if (pts.length === 1) {
        const p0 = pts[0]!;
        const renameIdx = onPage.find((i) => {
          const m = next[i]!;
          return (
            m.type === 'count' &&
            m.auto?.cat === 'columns' &&
            m.points.length === 1 &&
            !isAutoEdited(m) &&
            m.auto.des !== item.designation &&
            Math.hypot(m.points[0]!.x - p0.x, m.points[0]!.y - p0.y) <= 6
          );
        });
        if (renameIdx !== undefined) {
          matched.add(next[renameIdx]!.id);
          next[renameIdx] = update(next[renameIdx]!, item);
          summary.updated++;
          continue;
        }
      }
      const fresh = pts.filter((p) => {
        const hit = onPage.find((i) => {
          const m = next[i]!;
          return m.type === 'count' && m.points.some((q) => Math.hypot(q.x - p.x, q.y - p.y) <= 6);
        });
        if (hit !== undefined) matched.add(next[hit]!.id);
        return hit === undefined;
      });
      if (fresh.length === 0) {
        summary.duplicates++;
        continue;
      }
      if (fresh.length < pts.length) {
        summary.duplicates += pts.length - fresh.length;
        pushNew(build({ ...item, points: fresh.map((p) => [p.x, p.y] as [number, number]) }));
        summary.added++;
        continue;
      }
    }

    // 3. New.
    pushNew(build(item));
    summary.added++;
  }

  if (opts.removeStale) {
    const keep: M[] = [];
    for (const m of next) {
      const stale =
        m.auto &&
        !matched.has(m.id) &&
        opts.pages.has(m.page) &&
        opts.categories.has(m.auto.cat) &&
        (!opts.roles || !m.auto.role || opts.roles.has(m.auto.role)) &&
        !isAutoEdited(m);
      if (stale) summary.removed++;
      else keep.push(m);
    }
    return { next: keep, summary };
  }
  return { next, summary };
}

/** Human summary line for a merge. */
export function describeMerge(s: MergeSummary): string {
  const parts: string[] = [];
  parts.push(`${s.added} added`);
  if (s.updated) parts.push(`${s.updated} updated`);
  if (s.pointsAdded) parts.push(`${s.pointsAdded} column points added`);
  if (s.unchanged) parts.push(`${s.unchanged} already placed`);
  if (s.keptEdited) parts.push(`${s.keptEdited} kept (you edited them)`);
  if (s.duplicates) parts.push(`${s.duplicates} duplicates skipped`);
  if (s.rejected) parts.push(`${s.rejected} you deleted kept deleted`);
  if (s.removed) parts.push(`${s.removed} no longer found, removed`);
  return parts.join(' · ');
}

/** Paper inches per foot -> a viewer scale (metric-canonical, read in ft-in). */
export function scaleFromPaperInches(paperInPerFt: number): { pixelsPerUnit: number; unitLabel: string; displayUnit: 'ftin' } | null {
  if (!Number.isFinite(paperInPerFt) || paperInPerFt <= 0) return null;
  // 72 PDF units per paper inch; 1 ft = 12 in = 0.3048 m.
  return { pixelsPerUnit: (72 * paperInPerFt) / 0.3048, unitLabel: 'm', displayUnit: 'ftin' };
}

/** Extend (delta > 0) or shorten a straight line along its own direction.
 *  ``end`` 0 moves the start point, 1 the end point, 'both' splits it. */
export function extendLine(points: AutoPoint[], delta: number, end: 0 | 1 | 'both' = 1): AutoPoint[] {
  if (points.length < 2) return points;
  const a = points[0]!;
  const b = points[points.length - 1]!;
  const len = Math.hypot(b.x - a.x, b.y - a.y);
  if (len < 1e-6) return points;
  const ux = (b.x - a.x) / len;
  const uy = (b.y - a.y) / len;
  const minLen = 2;
  let d = delta;
  if (len + (end === 'both' ? 2 * d : d) < minLen) d = (minLen - len) / (end === 'both' ? 2 : 1);
  const out = points.map((p) => ({ ...p }));
  if (end === 1 || end === 'both') out[out.length - 1] = { x: b.x + ux * d, y: b.y + uy * d };
  if (end === 0 || end === 'both') out[0] = { x: a.x - ux * d, y: a.y - uy * d };
  return out;
}

/* ── one markup per column (OE-DELIVERY 2026-11-02-auto-takeoff-list) ── */

/** Key the server gives a single column at (x, y). */
export function columnKey(page: number, designation: string, x: number, y: number): string {
  return `${page}|columns|${designation}|${Math.round(x / 8)},${Math.round(y / 8)}`;
}

/** True when a list still holds an earlier run's combined column count. */
export function hasCombinedAutoCounts(list: AutoMeasurementLike[]): boolean {
  return list.some((m) => m.auto && m.type === 'count' && m.points.length > 1);
}

/**
 * Split combined auto column counts (one markup holding every column of a
 * sheet, as the first Auto Takeoff build placed them) into one markup per
 * column, so a single wrong column can be selected and deleted on its own.
 * ``clone`` builds the per-column markup; index 0 keeps the original id.
 */
export function splitAutoCounts<M extends AutoMeasurementLike>(
  list: M[],
  clone: (m: M, point: AutoPoint, index: number, tag: AutoTag) => M,
): { next: M[]; split: number } {
  let split = 0;
  const next: M[] = [];
  for (const m of list) {
    if (!(m.auto && m.type === 'count' && m.points.length > 1)) {
      next.push(m);
      continue;
    }
    split++;
    m.points.forEach((p, i) => {
      const tag: AutoTag = {
        ...m.auto!,
        key: columnKey(m.page, m.auto!.des, p.x, p.y),
        a: [p.x, p.y],
        h: pointsHash([p]),
      };
      next.push(clone(m, p, i, tag));
    });
  }
  return { next, split };
}

/** One row of the detected-markups list. */
export interface AutoListRow {
  id: string;
  cat: AutoCategory;
  des: string;
  page: number;
  /** Display quantity of this markup (length, area or count). */
  valueText: string;
  value: number;
  edited: boolean;
  generated: boolean;
  /** Profile / tag shown on the markup (C1 HSS8X8X1/2, W12X26 ...). */
  label?: string;
  /** Column height in feet, entered by the user. */
  heightFt?: number | null;
  /** Member role (Load Bearing Wall, Shear Wall ...), material / profile
   *  set on it, studs in a wall run and the markup colour
   *  (OE-DELIVERY 2026-11-08-stud-walls). */
  role?: string;
  material?: string;
  studs?: number;
  spacingIn?: number;
  widthIn?: number;
  segment?: 'wall' | 'header';
  colour?: string;
}

export interface AutoListGroup {
  des: string;
  rows: AutoListRow[];
  total: number;
}

/** Rows grouped category -> designation, designations by size of group. */
export function groupAutoRows(rows: AutoListRow[]): { cat: AutoCategory; count: number; groups: AutoListGroup[] }[] {
  const out: { cat: AutoCategory; count: number; groups: AutoListGroup[] }[] = [];
  for (const meta of AUTO_CATEGORIES) {
    const catRows = rows.filter((r) => r.cat === meta.key);
    if (catRows.length === 0) continue;
    const byDes = new Map<string, AutoListRow[]>();
    for (const r of catRows) {
      const list = byDes.get(r.des) ?? [];
      list.push(r);
      byDes.set(r.des, list);
    }
    const groups = [...byDes.entries()]
      .map(([des, list]) => ({
        des,
        rows: [...list].sort((a, b) => a.page - b.page),
        total: list.reduce((s, r) => s + r.value, 0),
      }))
      .sort((a, b) => b.rows.length - a.rows.length || a.des.localeCompare(b.des));
    out.push({ cat: meta.key, count: catRows.length, groups });
  }
  return out;
}

/* ── column height (OE-DELIVERY 2026-11-02-auto-takeoff-columns) ── */

/** "12'-6\"", "12' 6", "12.5", "150\"" -> feet; null when unreadable. */
export function parseFeetInches(text: string): number | null {
  const t = text.trim().replace(/[″”]/g, '"').replace(/[′’]/g, "'");
  if (!t) return null;
  let m = t.match(/^(\d+(?:\.\d+)?)\s*'\s*-?\s*(\d+(?:\.\d+)?)?(?:\s+(\d+)\/(\d+))?\s*"?$/);
  if (m) {
    const inches = (m[2] ? Number(m[2]) : 0) + (m[3] && m[4] ? Number(m[3]) / Number(m[4]) : 0);
    const ft = Number(m[1]) + inches / 12;
    return ft > 0 ? ft : null;
  }
  m = t.match(/^(\d+(?:\.\d+)?)\s*(?:"|in)$/i);
  if (m) return Number(m[1]) > 0 ? Number(m[1]) / 12 : null;
  m = t.match(/^(\d+(?:\.\d+)?)\s*(?:ft)?$/i);
  if (m) return Number(m[1]) > 0 ? Number(m[1]) : null;
  return null;
}

/** Feet -> 12'-6" or 27'-2 3/4" (nearest 1/4", fractions like Revu). */
export function formatFeetInches(ft: number | null | undefined): string {
  if (ft == null || !Number.isFinite(ft) || ft <= 0) return '';
  let whole = Math.floor(ft);
  let quarters = Math.round((ft - whole) * 12 * 4);
  if (quarters >= 48) {
    whole += 1;
    quarters -= 48;
  }
  const inches = Math.floor(quarters / 4);
  const frac = ['', ' 1/4', ' 1/2', ' 3/4'][quarters % 4];
  return `${whole}'-${inches}${frac}"`;
}

export const FT_TO_M = 0.3048;
