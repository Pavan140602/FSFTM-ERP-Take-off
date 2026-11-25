import { describe, expect, it } from 'vitest';
import { formatFtIn, parseLengthInches } from './length-input';

describe('parseLengthInches', () => {
  const cases: [string, 'ft' | 'in' | 'm', number][] = [
    ['12', 'ft', 144],
    ['12.0', 'ft', 144],
    ['12.5', 'ft', 150],
    ["12'", 'in', 144],
    ['12 ft', 'in', 144],
    ["12'-6\"", 'ft', 150],
    ["12' 6\"", 'ft', 150],
    ["12'6\"", 'ft', 150],
    ["12'-6 1/2\"", 'ft', 150.5],
    ["12'-6.5\"", 'ft', 150.5],
    ['12 ft 6 in', 'ft', 150],
    ["12'-6", 'ft', 150],
    ['6"', 'ft', 6],
    ['6 in', 'ft', 6],
    ['1/8"', 'ft', 0.125],
    ['3/4 in', 'ft', 0.75],
    ['1 1/2"', 'ft', 1.5],
    ['1-1/2"', 'ft', 1.5],
    ['300 mm', 'ft', 300 / 25.4],
    ['3.5 m', 'ft', 3.5 / 0.0254],
    ['2', 'm', 2 / 0.0254],
    ['1/8', 'in', 0.125],
  ];
  for (const [text, unit, want] of cases) {
    it(`${text} (${unit})`, () => {
      expect(parseLengthInches(text, unit)).toBeCloseTo(want, 6);
    });
  }
  it('rejects junk', () => {
    expect(parseLengthInches('abc', 'ft')).toBeNull();
    expect(parseLengthInches('', 'ft')).toBeNull();
  });
  it('formats', () => {
    expect(formatFtIn(150)).toBe(`12'-6"`);
    expect(formatFtIn(150.5)).toBe(`12'-6 1/2"`);
    expect(formatFtIn(0.125)).toBe(`0'-0 1/8"`);
  });
});
