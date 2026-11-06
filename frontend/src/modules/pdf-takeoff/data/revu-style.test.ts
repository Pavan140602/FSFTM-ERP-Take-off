// OE-DELIVERY: 2026-11-02-revu-properties
import { describe, expect, it } from 'vitest';
import {
  labelParts,
  lineDashFor,
  parseToolStyles,
  patchToolStyle,
  styleFieldsFor,
  wheelZoomFactor,
} from './revu-style';

describe('lineDashFor', () => {
  it('scales the pattern with the stroke and keeps solid empty', () => {
    expect(lineDashFor(undefined, 4)).toEqual([]);
    expect(lineDashFor('solid', 4)).toEqual([]);
    expect(lineDashFor('dashed', 2)).toEqual([12, 8]);
    expect(lineDashFor('dotted', 1)).toEqual([1, 3]);
    expect(lineDashFor('dashdot', 1)).toEqual([8, 3, 1, 3]);
    // Never shrinks below a 1px unit.
    expect(lineDashFor('dashed', 0.1)).toEqual([6, 4]);
  });
});

describe('labelParts', () => {
  it('maps each mode to the label lines it shows', () => {
    expect(labelParts(undefined)).toEqual({ name: true, value: true, material: true });
    expect(labelParts('value')).toEqual({ name: false, value: true, material: false });
    expect(labelParts('name')).toEqual({ name: true, value: false, material: true });
    expect(labelParts('none')).toEqual({ name: false, value: false, material: false });
  });
});

describe('tool styles', () => {
  it('patches, clears and drops empty tools', () => {
    let s = patchToolStyle({}, 'area', { color: '#ff0000', lineStyle: 'dashed', fillAlpha: 0.4 });
    expect(styleFieldsFor(s, 'area')).toEqual({ color: '#ff0000', lineStyle: 'dashed', fillAlpha: 0.4 });
    s = patchToolStyle(s, 'area', { lineStyle: undefined });
    expect(s.area).toEqual({ color: '#ff0000', fillAlpha: 0.4 });
    s = patchToolStyle(s, 'area', { color: undefined, fillAlpha: undefined });
    expect(s.area).toBeUndefined();
    expect(styleFieldsFor(s, 'distance')).toEqual({});
  });

  it('parses stored styles and rejects junk', () => {
    const raw = JSON.stringify({
      area: { color: '#00ff00', strokeWidth: 3, labelMode: 'value' },
      bad: { color: 'red', strokeWidth: 999, lineStyle: 'wavy' },
    });
    expect(parseToolStyles(raw)).toEqual({ area: { color: '#00ff00', strokeWidth: 3, labelMode: 'value' } });
    expect(parseToolStyles('not json')).toEqual({});
    expect(parseToolStyles(null)).toEqual({});
  });
});

describe('wheelZoomFactor', () => {
  it('steps 1.2x per mouse-wheel notch, glides for trackpads', () => {
    expect(wheelZoomFactor(-100, 0)).toBeCloseTo(1.2);
    expect(wheelZoomFactor(100, 0)).toBeCloseTo(1 / 1.2);
    expect(wheelZoomFactor(-3, 1)).toBeCloseTo(1.2 ** 3);
    const glide = wheelZoomFactor(-10, 0);
    expect(glide).toBeGreaterThan(1);
    expect(glide).toBeLessThan(1.05);
    expect(wheelZoomFactor(0, 0)).toBe(1);
    // A huge burst is capped at 4 notches.
    expect(wheelZoomFactor(-2000, 0)).toBeCloseTo(1.2 ** 4);
  });
});
