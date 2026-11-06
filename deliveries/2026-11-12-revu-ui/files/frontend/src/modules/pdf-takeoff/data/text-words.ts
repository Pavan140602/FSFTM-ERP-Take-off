// OE-DELIVERY: 2026-11-12-revu-ui (update 21 - text highlight + text select)
/**
 * Words on a PDF page with their boxes (viewport space at scale 1, y down),
 * so the Highlight tool can snap to the words a drag covers and the Text
 * Select tool can copy them. Text items are split into words with a width
 * per character estimate (pdf.js gives one width per item).
 */
export interface Word {
  str: string;
  x: number;
  y: number; // top
  w: number;
  h: number;
  /** Baseline, used to group words into lines. */
  base: number;
}

export interface RawItem {
  str: string;
  /** Baseline-left point in viewport space. */
  x: number;
  y: number;
  /** Font height and item width in viewport units. */
  h: number;
  w: number;
}

/** Split text items into words with boxes. */
export function wordsFromItems(items: RawItem[]): Word[] {
  const out: Word[] = [];
  for (const it of items) {
    const s = it.str;
    if (!s || !s.trim() || it.h <= 0) continue;
    const per = it.w > 0 ? it.w / s.length : it.h * 0.5;
    const re = /\S+/g;
    let m: RegExpExecArray | null;
    while ((m = re.exec(s))) {
      out.push({ str: m[0], x: it.x + m.index * per, y: it.y - it.h * 0.85, w: m[0].length * per, h: it.h * 1.1, base: it.y });
    }
  }
  return out;
}

/** Words whose centre lies inside the rectangle. */
export function wordsInRect(words: Word[], r: { x0: number; y0: number; x1: number; y1: number }): Word[] {
  const x0 = Math.min(r.x0, r.x1);
  const x1 = Math.max(r.x0, r.x1);
  const y0 = Math.min(r.y0, r.y1);
  const y1 = Math.max(r.y0, r.y1);
  return words.filter((w) => {
    const cx = w.x + w.w / 2;
    const cy = w.y + w.h / 2;
    return cx >= x0 && cx <= x1 && cy >= y0 && cy <= y1;
  });
}

/** Group words into lines (same baseline), left to right. */
export function linesOf(words: Word[]): Word[][] {
  const sorted = [...words].sort((a, b) => a.base - b.base || a.x - b.x);
  const lines: Word[][] = [];
  for (const w of sorted) {
    const ln = lines.find((l) => Math.abs(l[0]!.base - w.base) <= Math.max(l[0]!.h, w.h) * 0.4);
    if (ln) ln.push(w);
    else lines.push([w]);
  }
  for (const l of lines) l.sort((a, b) => a.x - b.x);
  return lines.sort((a, b) => a[0]!.base - b[0]!.base);
}

/** One box per line around its words (the text highlight shape). */
export function lineBoxes(words: Word[]): { x: number; y: number; w: number; h: number }[] {
  return linesOf(words).map((l) => {
    const x = Math.min(...l.map((w) => w.x));
    const y = Math.min(...l.map((w) => w.y));
    const r = Math.max(...l.map((w) => w.x + w.w));
    const b = Math.max(...l.map((w) => w.y + w.h));
    return { x, y, w: r - x, h: b - y };
  });
}

/** The selected text, line by line. */
export function textOf(words: Word[]): string {
  return linesOf(words).map((l) => l.map((w) => w.str).join(' ')).join('\n');
}
