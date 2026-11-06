// OE-DELIVERY: 2026-11-07-column-shapes
import { describe, expect, it } from 'vitest';
import { columnProfileOf, columnShape, isColumnMarkup, isManualColumn, profileKey } from './column-shape';

describe('columnShape', () => {
  it('reads wide flange sections', () => {
    expect(columnShape('W18X158').kind).toBe('wide-flange');
    expect(columnShape('W14 X 90').d).toBe(14);
    expect(columnShape('HP12X53').kind).toBe('wide-flange');
  });
  it('tells square from rectangular tube', () => {
    expect(columnShape('HSS8X8X1/2')).toMatchObject({ kind: 'hss-square', d: 8, b: 8 });
    expect(columnShape('HSS8X4X1/4')).toMatchObject({ kind: 'hss-rect', d: 8, b: 4 });
    expect(columnShape('HSS4X8X1/4')).toMatchObject({ kind: 'hss-rect', d: 8, b: 4 });
  });
  it('reads round tube and pipe as round', () => {
    expect(columnShape('HSS6.625X.280').kind).toBe('round');
    expect(columnShape('PIPE6STD').kind).toBe('round');
  });
  it('leaves an unknown size unknown', () => {
    expect(columnShape('COLUMN').kind).toBe('unknown');
    expect(columnShape('').kind).toBe('unknown');
  });
});

describe('columns placed by hand', () => {
  it('a count with a column profile or a Column subject is a column', () => {
    expect(isManualColumn({ type: 'count', customFields: { Material: 'HSS6X6X1/2' } })).toBe(true);
    expect(isManualColumn({ type: 'count', customFields: { Subject: 'Column' } })).toBe(true);
    expect(isManualColumn({ type: 'count', annotation: 'W12X65' })).toBe(true);
  });
  it('other markups are not', () => {
    expect(isManualColumn({ type: 'count', customFields: { Subject: 'Holdown' } })).toBe(false);
    expect(isManualColumn({ type: 'distance', customFields: { Material: 'W12X26' } })).toBe(false);
    expect(isManualColumn({ type: 'count', auto: { cat: 'columns', des: 'HSS8X8X1/2' } })).toBe(false);
    expect(isColumnMarkup({ type: 'count', auto: { cat: 'columns', des: 'HSS8X8X1/2' } })).toBe(true);
  });
  it('profile: the size set on it first, then what Auto Takeoff read', () => {
    expect(columnProfileOf({ type: 'count', customFields: { Material: 'HSS6X6X1/4' }, auto: { des: 'COLUMN' } })).toBe('HSS6X6X1/4');
    expect(columnProfileOf({ type: 'count', auto: { des: 'W18X143' } })).toBe('W18X143');
    expect(profileKey('hss 6x6x1/2')).toBe(profileKey('HSS6X6X1/2'));
  });
});
