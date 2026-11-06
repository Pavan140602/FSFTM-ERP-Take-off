// OE-DELIVERY: 2026-11-02-revu-left-panel
import { describe, expect, it } from 'vitest';
import { detectSheet, sheetCaption, type TextItemLite } from './sheet-index';

const t = (str: string, x: number, y: number, h = 8): TextItemLite => ({ str, x, y, h, w: str.length * h * 0.6 });

describe('detectSheet', () => {
  it('reads a right-strip title block (number + title below)', () => {
    const items = [
      t('W12X26', 900, 300), t('4', 400, 140, 9), t('S6.11', 780, 140, 7), // body text, grid / section marks
      t('S4.01a', 2440, 1580, 36),
      t('4TH FLOOR FRAMING', 2440, 1625, 9), t('PLAN - PART A', 2450, 1640, 9),
      t('Project No', 2430, 1340, 8), t('Revisions', 2430, 1400, 8),
    ];
    const r = detectSheet(items, 2592, 1728)!;
    expect(r.num).toBe('S4.01a');
    expect(r.title).toBe('4TH FLOOR FRAMING PLAN - PART A');
  });

  it('reads a bottom title block (SHEET NO. + DWG TITLE)', () => {
    const items = [
      t('C 9X13.4', 600, 500), t('S-1', 2300, 1640, 22), t('SHEET NO.', 2290, 1610, 9),
      t('DWG TITLE', 820, 1610, 9), t('ROOF FRAMING PLAN', 860, 1640, 12), t('DATE DRAWN', 820, 1580, 9),
    ];
    const r = detectSheet(items, 2592, 1728)!;
    expect(r.num).toBe('S-1');
    expect(r.title).toBe('ROOF FRAMING PLAN');
  });

  it('keeps the title when the sheet number is drawn as outlines', () => {
    const items = [t('LEGEND', 2636, 1660, 12), t('Project No', 2843, 1679, 12), t('SECOND FLOOR', 2872, 2082, 12), t('FRAMING PLAN', 2875, 2097, 12)];
    const r = detectSheet(items, 3024, 2160)!;
    expect(r.num).toBe('');
    expect(r.title).toBe('SECOND FLOOR FRAMING PLAN');
  });

  it('returns null when no title block number exists', () => {
    expect(detectSheet([t('NOTES', 100, 100), t('A1', 120, 140)], 612, 792)).toBeNull();
  });

  it('builds a caption', () => {
    expect(sheetCaption({ num: 'S-1', title: 'ROOF FRAMING PLAN' })).toBe('S-1 · ROOF FRAMING PLAN');
    expect(sheetCaption({ num: 'S-1', title: '' })).toBe('S-1');
  });
});
