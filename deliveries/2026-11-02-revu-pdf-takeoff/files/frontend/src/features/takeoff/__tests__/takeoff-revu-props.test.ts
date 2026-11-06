import { describe, expect, it } from 'vitest';
import { captionOptionsFor, cleanLabelStyle, labelStyleOf, selectionTotals } from '../lib/takeoff-revu-props';
import { captionValueText, formatInUnits, measurementLabel } from '../lib/takeoff-display-units';
import type { Measurement } from '../lib/takeoff-types';
import type { ScaleConfig } from '@/modules/pdf-takeoff/data/scale-helpers';

const scale = { pixelsPerUnit: 100, unitLabel: 'm' } as unknown as ScaleConfig;
const line = (over: Partial<Measurement> = {}): Measurement =>
  ({ id: 'a', type: 'distance', points: [{ x: 0, y: 0 }, { x: 100, y: 0 }], value: 3.048, unit: 'm', label: '', annotation: '', page: 1, group: 'G', ...over }) as Measurement;

describe('revu properties bar helpers', () => {
  it('formats a markup in its own units, km and square units included', () => {
    expect(formatInUnits(1500, 'm', scale, 'metric', 'km')).toMatch(/^1[.,]50? km$/);
    expect(formatInUnits(3.048, 'm', scale, 'metric', 'ft')).toMatch(/^10(.00)? ft$/);
    expect(formatInUnits(0.09290304, 'm²', scale, 'metric', undefined, 'sq ft')).toMatch(/^1(.0+)? sq ft$/);
    expect(formatInUnits(1, 'm²', scale, 'metric', undefined, 'sq mm')).toMatch(/^1.?000.?000(.0)? sq mm$/);
  });
  it('measurementLabel honours the markup unit', () => {
    expect(measurementLabel(line({ dispUnit: 'mm' }), scale, 'metric')).toMatch(/3.?048(.0)? mm/);
    expect(measurementLabel(line({ dispUnit: 'ftin' }), scale, 'metric')).toBe("10'-0\"");
  });
  it('builds captions from the pick list', () => {
    const wall = line({ wallHeight: 2, captions: ['length', 'wallArea', 'depth'], dispUnit: 'm' });
    const txt = captionValueText(wall, scale, 'metric');
    expect(txt).toContain('WA:');
    expect(txt).toContain('D:');
    expect(captionValueText(line({ captions: ['label'] }), scale, 'metric')).toBe('');
  });
  it('offers captions per tool', () => {
    expect(captionOptionsFor('distance')).toEqual(['label', 'length', 'wallArea', 'depth']);
    expect(captionOptionsFor('area')).toContain('perimeter');
    expect(captionOptionsFor('count')).toEqual(['label', 'count']);
  });
  it('cleans label style input', () => {
    expect(cleanLabelStyle({ labelBold: true, labelTextSize: 1000, dispUnit: 'yd', captions: ['label', 'x', 'label'] })).toEqual({ labelBold: true, captions: ['label'] });
    expect(labelStyleOf({})).toBeNull();
  });
  it('totals a selection', () => {
    const t = selectionTotals([
      { type: 'distance', value: 2, points: [] },
      { type: 'distance', value: 3, points: [], wallHeight: 2 },
      { type: 'area', value: 10, points: [] },
      { type: 'count', value: 3, points: [1, 2, 3] },
    ]);
    expect(t).toEqual({ length: 5, area: 16, volume: 0, count: 3, n: 4 });
  });
});
