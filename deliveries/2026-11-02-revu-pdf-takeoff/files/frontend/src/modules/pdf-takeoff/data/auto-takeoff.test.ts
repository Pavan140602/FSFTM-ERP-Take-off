// OE-DELIVERY: 2026-11-02-auto-takeoff
import { describe, expect, it } from 'vitest';
import {
  type AutoItem,
  type AutoMeasurementLike,
  columnKey,
  extendLine,
  groupAutoRows,
  hasCombinedAutoCounts,
  splitAutoCounts,
  isAutoEdited,
  itemPoints,
  linesOverlap,
  mergeAutoItems,
  pointsHash,
  normalizeProfile,
  parseFeetInches,
  formatFeetInches,
  rejectedFrom,
  scaleFromPaperInches,
  tagForItem,
} from './auto-takeoff';

let seq = 0;
const build = (item: AutoItem): AutoMeasurementLike => {
  const pts = itemPoints(item);
  return {
    id: `m${++seq}`,
    type: item.kind === 'line' ? 'distance' : item.kind === 'count' ? 'count' : 'area',
    points: pts,
    page: item.page,
    annotation: item.label,
    auto: tagForItem(item, pts),
  };
};
const update = (m: AutoMeasurementLike, item: AutoItem): AutoMeasurementLike => {
  const pts = itemPoints(item);
  return { ...m, points: pts, annotation: item.label, auto: tagForItem(item, pts) };
};

const beam = (over: Partial<AutoItem> = {}): AutoItem => ({
  key: '23|beams|W12X26|10,10',
  category: 'beams',
  kind: 'line',
  designation: 'W12X26',
  label: 'W12X26',
  spec: null,
  points: [
    [100, 100],
    [400, 100],
  ],
  anchor: [250, 96],
  page: 23,
  series: null,
  index: null,
  generated: false,
  confidence: 0.85,
  source: 'rules',
  ...over,
});
const opts = (removeStale = false) => ({ pages: new Set([23]), categories: new Set(['beams', 'columns', 'areas']), removeStale });

describe('mergeAutoItems', () => {
  it('adds new items on the first run', () => {
    const r = mergeAutoItems([], [beam()], build, update, opts());
    expect(r.next).toHaveLength(1);
    expect(r.summary.added).toBe(1);
  });

  it('never duplicates on a re-run with the same result', () => {
    const first = mergeAutoItems([], [beam()], build, update, opts()).next;
    const again = mergeAutoItems(first, [beam()], build, update, opts());
    expect(again.next).toHaveLength(1);
    expect(again.summary.added).toBe(0);
    expect(again.summary.unchanged).toBe(1);
  });

  it('updates an unedited markup when a re-run is more accurate', () => {
    const first = mergeAutoItems([], [beam()], build, update, opts()).next;
    const better = beam({ points: [[96, 100], [410, 100]] });
    const r = mergeAutoItems(first, [better], build, update, opts());
    expect(r.next).toHaveLength(1);
    expect(r.summary.updated).toBe(1);
    expect(r.next[0]!.points[1]!.x).toBe(410);
    expect(r.next[0]!.id).toBe(first[0]!.id);
  });

  it('keeps the user edit: a moved / extended markup is never overwritten', () => {
    const first = mergeAutoItems([], [beam()], build, update, opts()).next;
    const edited = [{ ...first[0]!, points: [{ x: 100, y: 100 }, { x: 450, y: 100 }] }];
    expect(isAutoEdited(edited[0]!)).toBe(true);
    const r = mergeAutoItems(edited, [beam({ points: [[96, 100], [410, 100]] })], build, update, opts(true));
    expect(r.next).toHaveLength(1);
    expect(r.summary.keptEdited).toBe(1);
    expect(r.next[0]!.points[1]!.x).toBe(450);
  });

  it('matches the same label across a key rounding boundary', () => {
    const first = mergeAutoItems([], [beam()], build, update, opts()).next;
    const r = mergeAutoItems(first, [beam({ key: '23|beams|W12X26|11,10', anchor: [254, 96] })], build, update, opts());
    expect(r.next).toHaveLength(1);
  });

  it('skips an item lying on a markup drawn by hand', () => {
    const manual: AutoMeasurementLike = { id: 'hand', type: 'distance', page: 23, points: [{ x: 102, y: 101 }, { x: 398, y: 101 }] };
    const r = mergeAutoItems([manual], [beam()], build, update, opts());
    expect(r.next).toHaveLength(1);
    expect(r.summary.duplicates).toBe(1);
  });

  it('removes unedited auto markups no longer found, only in the run scope', () => {
    const first = mergeAutoItems([], [beam(), beam({ key: 'x', page: 24, anchor: [0, 0] })], build, update, opts()).next;
    const r = mergeAutoItems(first, [], build, update, opts(true));
    expect(r.summary.removed).toBe(1);
    expect(r.next.map((m) => m.page)).toEqual([24]);
  });

  it('adds only new column points to an existing count', () => {
    const col = beam({ key: '23|columns|COLUMN|0,0', category: 'columns', kind: 'count', designation: 'COLUMN', label: 'COLUMN', points: [[10, 10], [200, 10]] });
    const first = mergeAutoItems([], [col], build, update, opts()).next;
    const r = mergeAutoItems(first, [{ ...col, points: [[10, 11], [200, 10], [400, 10]] }], build, update, opts());
    expect(r.next).toHaveLength(1);
    expect(r.next[0]!.points).toHaveLength(3);
    expect(r.summary.pointsAdded).toBe(1);
  });

  it('does not stack bay areas', () => {
    const bay = beam({ key: 'bay', category: 'areas', kind: 'area', points: [[0, 0], [100, 0], [100, 50], [0, 50]] });
    const first = mergeAutoItems([], [bay], build, update, opts()).next;
    const r = mergeAutoItems(first, [{ ...bay, key: 'bay2', anchor: [500, 500], points: [[1, 0], [101, 0], [101, 50], [1, 50]] }], build, update, opts());
    expect(r.next).toHaveLength(1);
  });
});

describe('geometry helpers', () => {
  it('linesOverlap ignores parallel lines further apart than the tolerance', () => {
    expect(linesOverlap([{ x: 0, y: 0 }, { x: 100, y: 0 }], [{ x: 0, y: 10 }, { x: 100, y: 10 }])).toBe(false);
    expect(linesOverlap([{ x: 0, y: 0 }, { x: 100, y: 0 }], [{ x: 50, y: 1 }, { x: 140, y: 1 }])).toBe(false);
    expect(linesOverlap([{ x: 0, y: 0 }, { x: 100, y: 0 }], [{ x: 10, y: 1 }, { x: 100, y: 1 }])).toBe(true);
  });

  it('extendLine grows and shrinks along the line, never below 2 units', () => {
    const l = [{ x: 0, y: 0 }, { x: 10, y: 0 }];
    expect(extendLine(l, 5)[1]).toEqual({ x: 15, y: 0 });
    expect(extendLine(l, 5, 0)[0]).toEqual({ x: -5, y: 0 });
    expect(extendLine(l, -20)[1]!.x).toBeCloseTo(2);
  });

  it('pointsHash is stable to sub-quarter-unit noise', () => {
    expect(pointsHash([{ x: 1.01, y: 2 }])).toBe(pointsHash([{ x: 1.02, y: 2 }]));
  });

  it('scaleFromPaperInches gives 1/8"=1\'-0" in metres', () => {
    const s = scaleFromPaperInches(0.125)!;
    // 1 ft = 9 PDF units at 1/8" scale -> 9 / 0.3048 px per metre.
    expect(s.pixelsPerUnit).toBeCloseTo(9 / 0.3048, 6);
  });
});

describe('one markup per column', () => {
  it('splits an earlier combined column count, keeping the first id', () => {
    const combined: AutoMeasurementLike = {
      id: 'c1',
      type: 'count',
      page: 3,
      points: [{ x: 10, y: 10 }, { x: 200, y: 10 }, { x: 400, y: 10 }],
      auto: { key: '3|columns|COLUMN|0,0', cat: 'columns', des: 'COLUMN', a: [10, 10], src: 'rules', h: 'x' },
    };
    const other: AutoMeasurementLike = { id: 'b', type: 'distance', page: 3, points: [{ x: 0, y: 0 }, { x: 5, y: 0 }] };
    expect(hasCombinedAutoCounts([combined])).toBe(true);
    const r = splitAutoCounts([combined, other], (m, p, i, tag) => ({ ...m, id: i === 0 ? m.id : `${m.id}_${i}`, points: [p], auto: tag }));
    expect(r.split).toBe(1);
    expect(r.next.map((m) => m.id)).toEqual(['c1', 'c1_1', 'c1_2', 'b']);
    expect(r.next.every((m) => !isAutoEdited(m))).toBe(true);
    expect(hasCombinedAutoCounts(r.next)).toBe(false);
  });

  it('a re-run with single-column items matches the split markups, no duplicates', () => {
    const col = (x: number): AutoItem => beam({ key: columnKey(23, 'COLUMN', x, 10), category: 'columns', kind: 'count', designation: 'COLUMN', label: 'COLUMN', points: [[x, 10]], anchor: [x, 10] });
    const first = mergeAutoItems([], [col(10), col(200)], build, update, opts()).next;
    expect(first).toHaveLength(2);
    const r = mergeAutoItems(first, [col(10), col(200), col(400)], build, update, opts());
    expect(r.next).toHaveLength(3);
    expect(r.summary.added).toBe(1);
  });

  it('groupAutoRows groups by category then designation', () => {
    const rows = [
      { id: '1', cat: 'beams' as const, des: 'W12X26', page: 2, valueText: '', value: 3, edited: false, generated: false },
      { id: '2', cat: 'beams' as const, des: 'W12X26', page: 1, valueText: '', value: 4, edited: false, generated: false },
      { id: '3', cat: 'columns' as const, des: 'COLUMN', page: 1, valueText: '', value: 1, edited: false, generated: false },
    ];
    const g = groupAutoRows(rows);
    expect(g.map((c) => c.cat)).toEqual(['beams', 'columns']);
    expect(g[0]!.groups[0]!.total).toBe(7);
    expect(g[0]!.groups[0]!.rows[0]!.page).toBe(1);
  });
});

describe('deleted auto markups stay deleted', () => {
  it('a re-run does not bring back a markup the user deleted', () => {
    const first = mergeAutoItems([], [beam()], build, update, opts()).next;
    const rej = rejectedFrom(first[0]!)!;
    const r = mergeAutoItems([], [beam({ key: 'other-key', anchor: [252, 97] })], build, update, { ...opts(), rejected: [rej] });
    expect(r.next).toHaveLength(0);
    expect(r.summary.rejected).toBe(1);
  });
});

describe('column height entry', () => {
  it('parses feet-inches the way estimators type it', () => {
    expect(parseFeetInches(`12'-6"`)).toBeCloseTo(12.5);
    expect(parseFeetInches(`12' 6`)).toBeCloseTo(12.5);
    expect(parseFeetInches('12.5')).toBeCloseTo(12.5);
    expect(parseFeetInches('150"')).toBeCloseTo(12.5);
    expect(parseFeetInches(`10'-3 1/2"`)).toBeCloseTo(10 + 3.5 / 12);
    expect(parseFeetInches('abc')).toBeNull();
    expect(formatFeetInches(12.5)).toBe(`12'-6"`);
    expect(formatFeetInches(27 + 2.75 / 12)).toBe(`27'-2 3/4"`);
    expect(formatFeetInches(11.999)).toBe(`12'-0"`);
  });

  it('keeps the profile text rect on the tag', () => {
    const tag = tagForItem(beam({ label_rect: [1, 2, 3, 4] }));
    expect(tag.lr).toEqual([1, 2, 3, 4]);
  });
});

describe('column profile arrives on a later run', () => {
  it('renames an unedited COLUMN markup to its profile in place', () => {
    const col = (des: string): AutoItem => beam({ key: columnKey(23, des, 100, 10), category: 'columns', kind: 'count', designation: des, label: des, points: [[100, 10]], anchor: [100, 10] });
    const first = mergeAutoItems([], [col('COLUMN')], build, update, opts()).next;
    const r = mergeAutoItems(first, [col('HSS22X22X7/8')], build, update, opts());
    expect(r.next).toHaveLength(1);
    expect(r.next[0]!.id).toBe(first[0]!.id);
    expect(r.next[0]!.auto!.des).toBe('HSS22X22X7/8');
  });
});

describe('profile edited by the user', () => {
  it('a re-run never overwrites a profile the user set', () => {
    const first = mergeAutoItems([], [beam()], build, update, opts()).next;
    const edited = [{ ...first[0]!, annotation: 'W14X30', auto: { ...first[0]!.auto!, des: 'W14X30', ud: true } }];
    expect(isAutoEdited(edited[0]!)).toBe(true);
    const r = mergeAutoItems(edited, [beam()], build, update, opts(true));
    expect(r.next).toHaveLength(1);
    expect(r.next[0]!.annotation).toBe('W14X30');
    expect(r.summary.keptEdited).toBe(1);
  });

  it('a column the user named is not renamed by a later run', () => {
    const col = (des: string): AutoItem => beam({ key: columnKey(23, 'COLUMN', 100, 10), category: 'columns', kind: 'count', designation: des, label: des, points: [[100, 10]], anchor: [100, 10] });
    const first = mergeAutoItems([], [col('COLUMN')], build, update, opts()).next;
    const named = [{ ...first[0]!, annotation: 'HSS6X6X1/4', auto: { ...first[0]!.auto!, des: 'HSS6X6X1/4', ud: true } }];
    const r = mergeAutoItems(named, [{ ...col('HSS22X22X7/8'), key: 'k2' }], build, update, opts());
    expect(r.next).toHaveLength(1);
    expect(r.next[0]!.annotation).toBe('HSS6X6X1/4');
  });

  it('normalizes typed profiles', () => {
    expect(normalizeProfile('  w12x26 ')).toBe('W12X26');
    expect(normalizeProfile('c1   hss8x8x1/2')).toBe('C1 HSS8X8X1/2');
  });
});
