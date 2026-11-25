import { describe, expect, it } from 'vitest';
import { lineBoxes, textOf, wordsFromItems, wordsInRect } from './text-words';

describe('text-words', () => {
  const items = [
    { str: 'ALL STEEL SHALL BE', x: 100, y: 200, h: 10, w: 180 },
    { str: 'ASTM A992 GRADE 50', x: 100, y: 214, h: 10, w: 180 },
  ];
  const words = wordsFromItems(items);
  it('splits items into words', () => {
    expect(words.map((w) => w.str)).toEqual(['ALL', 'STEEL', 'SHALL', 'BE', 'ASTM', 'A992', 'GRADE', '50']);
  });
  it('picks the words a rectangle covers and gives one box per line', () => {
    const sel = wordsInRect(words, { x0: 130, y0: 185, x1: 230, y1: 216 });
    expect(textOf(sel)).toBe('STEEL SHALL\nA992 GRADE');
    expect(lineBoxes(sel)).toHaveLength(2);
  });
});
