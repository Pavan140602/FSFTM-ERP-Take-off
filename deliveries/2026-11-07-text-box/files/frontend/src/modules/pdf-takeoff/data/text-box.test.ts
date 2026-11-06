// OE-DELIVERY: 2026-11-07-text-box
import { describe, expect, it } from 'vitest';
import { cleanTextStyle, DEFAULT_TEXT_STYLE, LEGACY_TEXT_STYLE, layoutTextBox, resolveTextStyle, wrapText } from './text-box';

// Fixed-width measure so the tests do not depend on canvas fonts.
const mono = (t: string) => t.length * 6;

describe('text box layout', () => {
  it('wraps on words and keeps typed line breaks', () => {
    const s = { ...DEFAULT_TEXT_STYLE, size: 10 };
    expect(wrapText('aaa bbb ccc', 40, s, mono)).toEqual(['aaa', 'bbb', 'ccc']);
    expect(wrapText('aaa bbb\nccc', 60, s, mono)).toEqual(['aaa bbb', 'ccc']);
    expect(wrapText('line one\n\nline three', 200, s, mono)).toEqual(['line one', '', 'line three']);
  });

  it('breaks a word longer than the box', () => {
    const s = { ...DEFAULT_TEXT_STYLE, size: 6 };
    expect(wrapText('abcdefghij', 30, s, mono)).toEqual(['abcde', 'fghij']);
  });

  it('box height grows with lines, size and padding', () => {
    const s = { ...DEFAULT_TEXT_STYLE, size: 10, lineHeight: 1.2, padding: 4, borderWidth: 1 };
    const one = layoutTextBox('abc', 200, s, mono);
    const two = layoutTextBox('abc\ndef', 200, s, mono);
    expect(one.lines).toEqual(['abc']);
    expect(two.contentHeight - one.contentHeight).toBeCloseTo(12);
    expect(one.contentHeight).toBeCloseTo(12 + 8 + 1);
  });
});

describe('text box style', () => {
  it('keeps only valid saved values', () => {
    expect(
      cleanTextStyle({ font: 'Calibri', size: 9999, bold: true, align: 'middle', color: 'red', fill: null, border: '#FF0000', borderStyle: 'cloud', opacity: 0 }),
    ).toEqual({ font: 'Calibri', size: 400, bold: true, fill: null, border: '#FF0000', borderStyle: 'cloud', opacity: 0.05 });
    expect(cleanTextStyle(null)).toBeUndefined();
    expect(cleanTextStyle({ nonsense: 1 })).toBeUndefined();
  });

  it('a box with no style of its own keeps the older bold-14 look', () => {
    expect(resolveTextStyle(undefined)).toBe(LEGACY_TEXT_STYLE);
    expect(resolveTextStyle({ size: 18 })).toMatchObject({ font: 'Arial', size: 18, bold: false });
  });
});
