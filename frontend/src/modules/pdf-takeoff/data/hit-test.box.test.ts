import { describe, expect, it } from 'vitest';
import { measurementTouchesBox, supportsVariableVertices } from './hit-test';

const line = { id: 'l', type: 'distance', points: [{ x: 0, y: 0 }, { x: 100, y: 100 }] } as never;
const lShape = {
  id: 'a',
  type: 'area',
  points: [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 20 }, { x: 20, y: 20 }, { x: 20, y: 100 }, { x: 0, y: 100 }],
} as never;

describe('measurementTouchesBox (marquee select)', () => {
  it('picks a diagonal line only where the box touches it', () => {
    expect(measurementTouchesBox(line, { x0: 45, y0: 45, x1: 55, y1: 55 })).toBe(true);
    // Inside the bounding box, but nowhere near the line.
    expect(measurementTouchesBox(line, { x0: 70, y0: 5, x1: 90, y1: 20 })).toBe(false);
  });
  it('tests areas on their outline and interior, not the bounding box', () => {
    expect(measurementTouchesBox(lShape, { x0: 60, y0: 60, x1: 90, y1: 90 })).toBe(false);
    expect(measurementTouchesBox(lShape, { x0: 5, y0: 40, x1: 10, y1: 50 })).toBe(true); // inside the fill
    expect(measurementTouchesBox(lShape, { x0: 90, y0: 10, x1: 120, y1: 30 })).toBe(true); // crosses an edge
  });
  it('accepts corners in any order', () => {
    expect(measurementTouchesBox(line, { x0: 55, y0: 55, x1: 45, y1: 45 })).toBe(true);
  });
  it('lets cutouts and perimeters take extra points', () => {
    expect(supportsVariableVertices('polygonCutout')).toBe(true);
    expect(supportsVariableVertices('perimeter')).toBe(true);
  });
});
