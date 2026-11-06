// OE-DELIVERY: 2026-11-02-revu-left-panel
/**
 * Sheet index: read each page's sheet number and title from its own text
 * (the title block), like Revu's page labels / bookmarks built from the
 * drawing. The user can edit every entry; edits win over detection.
 *
 * Pure: the viewer feeds pdf.js text items already mapped to page space
 * (top-left origin, PDF points).
 */

export interface SheetEntry {
  /** Sheet number, e.g. "S4.01a", "S-1", "A-101". */
  num: string;
  /** Sheet title, e.g. "4TH FLOOR FRAMING PLAN - PART A". */
  title: string;
}

export interface TextItemLite {
  str: string;
  /** Left of the text (page space, points). */
  x: number;
  /** Baseline y (page space, top-left origin). */
  y: number;
  /** Font height in points. */
  h: number;
  /** Text width in points (0 when unknown). */
  w: number;
}

const SHEET_NUM_RE = /^[A-Z]{1,3}[-.]?\d{1,3}(?:\.\d{1,3})?[A-Za-z]?$/;
const TITLE_WORDS = /\b(PLAN|PLANS|ELEVATIONS?|SECTIONS?|DETAILS?|SCHEDULES?|NOTES|FRAMING|FOUNDATION|ROOF|LAYOUT|DIAGRAM|COVER|INDEX|SPECIFICATIONS?|CONNECTIONS?|GENERAL|TRUSS|WALL|FLOOR|LEVEL|STAIR|ELEVATION)\b/i;
const NOT_TITLE = /^(PROJECT|DATE|DRAWN|CHECKED|REVISIONS?|REV|SCALE|SHEET|NO\.?|JOB|CLIENT|DWG TITLE|DRAWING TITLE|SHEET NO\.?|TITLE)\b/i;

function median(values: number[]): number {
  if (values.length === 0) return 0;
  const s = [...values].sort((a, b) => a - b);
  return s[Math.floor(s.length / 2)]!;
}

/** Detect the sheet number + title of one page, or null. */
export function detectSheet(items: TextItemLite[], pageW: number, pageH: number): SheetEntry | null {
  const clean = items
    .map((it) => ({ ...it, str: it.str.replace(/\s+/g, ' ').trim() }))
    .filter((it) => it.str.length > 0 && it.h > 0);
  if (clean.length === 0) return null;
  const med = median(clean.map((i) => i.h)) || 8;
  const inTitleBlock = (i: TextItemLite) => i.x > pageW * 0.68 || i.y > pageH * 0.82;

  // The sheet number: the largest sheet-number-shaped text in the title block.
  let best: (TextItemLite & { score: number }) | null = null;
  for (const it of clean) {
    if (!SHEET_NUM_RE.test(it.str) || !inTitleBlock(it)) continue;
    if (it.h < med * 1.4) continue; // grid bubbles / section marks are body size
    const score = it.h * (it.x > pageW * 0.8 ? 1.2 : 1) * (it.y > pageH * 0.7 ? 1.15 : 1);
    if (!best || score > best.score) best = { ...it, score };
  }
  // The title: title-block text with a drawing word, nearest the number
  // (or the title-block corner when the number is drawn as outlines);
  // stacked title lines ("4TH FLOOR FRAMING" / "PLAN - PART A") are joined.
  const refX = best ? best.x : pageW;
  const refY = best ? best.y : pageH;
  const cand = clean.filter(
    (it) =>
      it !== best &&
      inTitleBlock(it) &&
      it.str.length >= 4 &&
      /[A-Za-z]{3}/.test(it.str) &&
      TITLE_WORDS.test(it.str) &&
      !NOT_TITLE.test(it.str) &&
      it.str.toUpperCase() === it.str,
  );
  let title = '';
  if (cand.length > 0) {
    const pick = cand.reduce((a, b) => (Math.hypot(a.x - refX, a.y - refY) <= Math.hypot(b.x - refX, b.y - refY) ? a : b));
    const sameStyle = clean.filter(
      (it) =>
        inTitleBlock(it) &&
        it !== best &&
        Math.abs(it.h - pick.h) <= pick.h * 0.3 &&
        Math.abs(it.x - pick.x) < pageW * 0.05 &&
        !/^KEY PLAN$/i.test(it.str) &&
        !NOT_TITLE.test(it.str) &&
        /[A-Za-z]/.test(it.str) &&
        it.str.toUpperCase() === it.str,
    );
    // Group into lines, then grow from the picked line while lines stack.
    const lines: { y: number; items: TextItemLite[] }[] = [];
    for (const it of [...sameStyle].sort((a, b) => a.y - b.y)) {
      const ln = lines.find((l) => Math.abs(l.y - it.y) <= pick.h * 0.6);
      if (ln) ln.items.push(it);
      else lines.push({ y: it.y, items: [it] });
    }
    const at = lines.findIndex((l) => l.items.includes(pick));
    let lo = at;
    let hi = at;
    while (lo > 0 && lines[lo]!.y - lines[lo - 1]!.y <= pick.h * 2.1 && hi - lo < 2) lo--;
    while (hi < lines.length - 1 && lines[hi + 1]!.y - lines[hi]!.y <= pick.h * 2.1 && hi - lo < 2) hi++;
    title = lines
      .slice(lo, hi + 1)
      .map((l) => l.items.sort((a, b) => a.x - b.x).map((i) => i.str).join(' '))
      .join(' ')
      .replace(/\s+/g, ' ')
      .trim();
    if (title.length > 90) title = pick.str;
  }
  if (!best && !title) return null;
  return { num: best ? best.str : '', title };
}

/** "S4.01a · 4TH FLOOR FRAMING PLAN" (or whichever part exists). */
export function sheetCaption(e: SheetEntry | null | undefined): string {
  if (!e) return '';
  return [e.num, e.title].filter(Boolean).join(' · ');
}
