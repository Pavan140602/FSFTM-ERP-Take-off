// OE-DELIVERY: 2026-11-12-revu-ui (update 15 - Revu page tools + vector save)
/**
 * PDF page work on the real (vector) file, with pdf-lib:
 *  - Save PDF the Revu way: every page kept as it is, each markup written as
 *    a real PDF annotation (Revu / Acrobat / browsers show them), and the ERP
 *    snapshot embedded so the ERP reopens them as editable markups.
 *  - Page tools from the thumbnails menu: extract, delete, insert blank,
 *    insert / replace from another PDF, rotate, paste, repair.
 * The ERP snapshot (OE-TAKEOFF: in Keywords) carries the markups across a
 * page change: `pageMap` says where each original page went.
 */
import {
  PDFArray,
  PDFDict,
  PDFDocument,
  PDFRef,
  PDFHexString,
  PDFName,
  PDFNumber,
  PDFString,
  StandardFonts,
  degrees,
  type PDFFont,
} from 'pdf-lib';
import { TAKEOFF_SNAPSHOT_PREFIX, type TakeoffSnapshot } from '../../../features/takeoff/lib/takeoff-export';
import type { Measurement } from '../../../features/takeoff/lib/takeoff-types';
import type { ScaleConfig } from './scale-helpers';

type Pt = { x: number; y: number };

/** Snapshot with the page scales too (optional field, update 15). */
export type TakeoffSnapshotV = TakeoffSnapshot & { scales?: Record<string, ScaleConfig> };

/* ── Snapshot ─────────────────────────────────────────────────────── */

export function makeSnapshot(
  measurements: Measurement[],
  pageMap: Record<string, number>,
  pageSizes: Record<string, { w: number; h: number }>,
  scales?: Record<string, ScaleConfig>,
): TakeoffSnapshotV {
  return {
    v: 1,
    app: 'openconstructionerp-takeoff',
    exportedAt: new Date().toISOString(),
    pageMap,
    pageSizes,
    measurements,
    ...(scales ? { scales } : {}),
  };
}

function setSnapshot(doc: PDFDocument, snap: TakeoffSnapshotV | null): void {
  if (!snap || (snap.measurements.length === 0 && !(snap.scales && Object.keys(snap.scales).length))) {
    // Drop a stale snapshot from an earlier save.
    const kw = doc.getKeywords();
    if (kw && kw.startsWith(TAKEOFF_SNAPSHOT_PREFIX)) doc.setKeywords([]);
    return;
  }
  doc.setKeywords([`${TAKEOFF_SNAPSHOT_PREFIX}${JSON.stringify(snap)}`]);
}

/* ── Markups as PDF annotations ───────────────────────────────────── */

export interface AnnotInput {
  m: Measurement;
  /** Resolved colour (#rrggbb). */
  color: string;
  /** viewport (scale 1) point -> PDF user space. */
  toPdf: (p: Pt) => Pt;
  /** Text shown in the annotation's comment (label / value). */
  text: string;
  /** Dimension shown on the sheet next to the markup, e.g. 12'-6" or 45.2 sf. */
  dim?: string;
}

function rgb(hex: string): number[] {
  const h = (hex || '#ef4444').replace('#', '');
  const n = parseInt(h.length === 3 ? h.split('').map((c) => c + c).join('') : h.slice(0, 6), 16);
  if (!Number.isFinite(n)) return [0.94, 0.27, 0.27];
  return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255];
}

function bbox(pts: Pt[], pad: number): number[] {
  const xs = pts.map((p) => p.x);
  const ys = pts.map((p) => p.y);
  return [Math.min(...xs) - pad, Math.min(...ys) - pad, Math.max(...xs) + pad, Math.max(...ys) + pad];
}

const CLOSED = new Set(['area', 'volume', 'polygon', 'perimeter', 'polygonCutout', 'cloud', 'dynamicFill']);
const OPEN = new Set(['polyline', 'polylineMarkup']);
const LINES = new Set(['distance', 'line', 'arrow', 'diameter', 'radiusCenter', 'radius3Point', 'arc', 'angle']);
const BOXES = new Set(['rectangle', 'highlight', 'rectarea']);

/** Name of the PDF layer the ERP's annotations sit on. Other viewers show
 *  it (on by default); the ERP turns just this layer off when it reopens the
 *  file, so its editable markups are not doubled and the drawing's own
 *  annotations (e.g. Revu markups) still show (update 15). */
export const OE_LAYER = 'OE Markups';

/** The "OE Markups" optional-content group (made once, reused on re-save). */
function ensureLayer(doc: PDFDocument): PDFRef {
  const ctx = doc.context;
  const cat = doc.catalog;
  let props = cat.lookupMaybe(PDFName.of('OCProperties'), PDFDict);
  if (!props) {
    props = ctx.obj({ OCGs: [], D: { ON: [], Order: [] } }) as unknown as PDFDict;
    cat.set(PDFName.of('OCProperties'), props);
  }
  const ocgs = props.lookupMaybe(PDFName.of('OCGs'), PDFArray) ?? (() => { const a = PDFArray.withContext(ctx); props!.set(PDFName.of('OCGs'), a); return a; })();
  for (let i = 0; i < ocgs.size(); i++) {
    const ref = ocgs.get(i);
    const g = ctx.lookup(ref);
    if (g instanceof PDFDict) {
      const nm = g.get(PDFName.of('Name'));
      const txt = nm instanceof PDFString || nm instanceof PDFHexString ? nm.decodeText() : '';
      if (txt === OE_LAYER && ref instanceof PDFRef) return ref;
    }
  }
  const ref = ctx.register(ctx.obj({ Type: 'OCG', Name: PDFHexString.fromText(OE_LAYER) }));
  ocgs.push(ref);
  let d = props.lookupMaybe(PDFName.of('D'), PDFDict);
  if (!d) {
    d = ctx.obj({}) as unknown as PDFDict;
    props.set(PDFName.of('D'), d);
  }
  for (const key of ['ON', 'Order']) {
    const arr = d.lookupMaybe(PDFName.of(key), PDFArray) ?? (() => { const a = PDFArray.withContext(ctx); d!.set(PDFName.of(key), a); return a; })();
    arr.push(ref);
  }
  return ref;
}

/** Number for a content stream. */
const n2 = (v: number) => (Math.round(v * 100) / 100).toString();

/** A drawn appearance (/AP /N) in page coordinates: BBox = Rect, so the
 *  stream draws exactly where the annotation sits. Every viewer (Chrome,
 *  Edge, Acrobat, Revu, Bluebeam, pdf.js) then shows it the same. */
function apRef(doc: PDFDocument, rect: number[], ops: string, opts: { CA?: number; ca?: number; font?: PDFFont }): PDFRef {
  const resources: Record<string, unknown> = {
    ExtGState: { GS1: { Type: 'ExtGState', CA: opts.CA ?? 1, ca: opts.ca ?? opts.CA ?? 1 } },
  };
  if (opts.font) resources.Font = { F1: opts.font.ref };
  const stream = doc.context.stream(`/GS1 gs\n${ops}`, {
    Type: 'XObject',
    Subtype: 'Form',
    BBox: rect,
    Resources: resources,
  } as never);
  return doc.context.register(stream);
}

function pathOps(pts: Pt[], close: boolean): string {
  return pts.map((q, i) => `${n2(q.x)} ${n2(q.y)} ${i === 0 ? 'm' : 'l'}`).join('\n') + (close ? '\nh' : '');
}

function ellipseOps(cx: number, cy: number, rx: number, ry: number): string {
  const k = 0.5523;
  return [
    `${n2(cx + rx)} ${n2(cy)} m`,
    `${n2(cx + rx)} ${n2(cy + ry * k)} ${n2(cx + rx * k)} ${n2(cy + ry)} ${n2(cx)} ${n2(cy + ry)} c`,
    `${n2(cx - rx * k)} ${n2(cy + ry)} ${n2(cx - rx)} ${n2(cy + ry * k)} ${n2(cx - rx)} ${n2(cy)} c`,
    `${n2(cx - rx)} ${n2(cy - ry * k)} ${n2(cx - rx * k)} ${n2(cy - ry)} ${n2(cx)} ${n2(cy - ry)} c`,
    `${n2(cx + rx * k)} ${n2(cy - ry)} ${n2(cx + rx)} ${n2(cy - ry * k)} ${n2(cx + rx)} ${n2(cy)} c`,
  ].join('\n');
}

/** Scalloped (cloud) outline through a closed ring, bumps outward-ish. */
function cloudOps(pts: Pt[], r: number): string {
  const ring = [...pts, pts[0]!];
  const out: string[] = [];
  let first = true;
  for (let i = 0; i + 1 < ring.length; i++) {
    const a = ring[i]!;
    const b = ring[i + 1]!;
    const L = Math.hypot(b.x - a.x, b.y - a.y);
    if (L < 0.5) continue;
    const nB = Math.max(1, Math.round(L / (2 * r)));
    const ux = (b.x - a.x) / L;
    const uy = (b.y - a.y) / L;
    // Normal (PDF y-up, ring drawn in screen order -> pick the left normal).
    const nx = -uy;
    const ny = ux;
    const seg = L / nB;
    for (let k = 0; k < nB; k++) {
      const p0 = { x: a.x + ux * seg * k, y: a.y + uy * seg * k };
      const p1 = { x: a.x + ux * seg * (k + 1), y: a.y + uy * seg * (k + 1) };
      const h = seg * 0.65;
      if (first) { out.push(`${n2(p0.x)} ${n2(p0.y)} m`); first = false; }
      out.push(`${n2(p0.x + nx * h)} ${n2(p0.y + ny * h)} ${n2(p1.x + nx * h)} ${n2(p1.y + ny * h)} ${n2(p1.x)} ${n2(p1.y)} c`);
    }
  }
  return out.join('\n');
}

/** Add the markups of one page as PDF annotations (tagged NM "oe-<id>"),
 *  each with a drawn appearance, plus a dimension label per measurement. */
function addAnnots(doc: PDFDocument, pageIndex: number, items: AnnotInput[], font: PDFFont): number {
  const layer = ensureLayer(doc);
  const page = doc.getPage(pageIndex);
  const ctx = doc.context;
  let n = 0;
  const put = (dict: Record<string, unknown>) => {
    page.node.addAnnot(ctx.register(ctx.obj(dict as never)));
    n++;
  };
  /** A text label annotation (FreeText, no border) with its own appearance. */
  const label = (common: Record<string, unknown>, text: string, at: Pt, C: number[], size: number, id: string) => {
    const clean = text.replace(/[^\x20-\x7E\u00A0-\u00FF]/g, (ch) => (ch === '\u00B2' || ch === '\u00B3' ? ch : ''));
    if (!clean.trim()) return;
    const w = font.widthOfTextAtSize(clean, size) + 4;
    const h = size * 1.35;
    const rect = [at.x - w / 2, at.y - h / 2, at.x + w / 2, at.y + h / 2];
    const ops = `1 1 1 rg ${n2(rect[0]!)} ${n2(rect[1]!)} ${n2(w)} ${n2(h)} re f\nBT /F1 ${size} Tf ${C.map(n2).join(' ')} rg ${n2(rect[0]! + 2)} ${n2(rect[1]! + size * 0.32)} Td ${font.encodeText(clean).toString()} Tj ET`;
    put({
      ...common,
      Subtype: 'FreeText',
      NM: PDFString.of(`oe-${id}-dim`),
      Rect: rect,
      Contents: PDFHexString.fromText(clean),
      DA: PDFString.of(`/Helv ${size} Tf ${C.map(n2).join(' ')} rg`),
      BS: { W: 0 },
      CA: 1,
      AP: { N: apRef(doc, rect, ops, { CA: 1, font }) },
    });
  };
  for (const { m, color, toPdf, text, dim } of items) {
    if (!m.points || m.points.length === 0) continue;
    const pts = m.points.map(toPdf);
    const w = Math.max(0.5, Number(m.strokeWidth ?? 2) * 0.75);
    const C = rgb(color);
    const CA = Math.max(0.05, Math.min(1, Number(m.strokeAlpha ?? 1)));
    const dash = m.lineStyle === 'dashed' ? '[6 3] 0 d\n' : m.lineStyle === 'dotted' ? '[1 2] 0 d\n' : '';
    const strokeHead = `${C.map(n2).join(' ')} RG ${n2(w)} w 1 J 1 j\n${dash}`;
    const common: Record<string, unknown> = {
      Type: 'Annot',
      C,
      F: 4,
      BS: { W: w, S: dash ? 'D' : 'S' },
      CA,
      NM: PDFString.of(`oe-${m.id}`),
      Contents: PDFHexString.fromText([text, dim].filter(Boolean).join(' - ')),
      Subj: PDFHexString.fromText(String(m.customFields?.Subject || m.type)),
      T: PDFHexString.fromText(String(m.author || 'OpenConstructionERP')),
      OC: layer,
    };
    const pad = w + 2;
    if (m.type === 'count') {
      for (const q of pts) {
        const rect = [q.x - 5, q.y - 5, q.x + 5, q.y + 5];
        put({ ...common, Subtype: 'Circle', Rect: rect, IC: C, AP: { N: apRef(doc, rect, `${C.map(n2).join(' ')} rg ${ellipseOps(q.x, q.y, 4, 4)} f`, { CA }) } });
      }
      if (dim && pts[0]) label(common, dim, { x: pts[0].x + 14, y: pts[0].y + 10 }, C, 8, m.id);
      continue;
    }
    if (CLOSED.has(m.type) && pts.length >= 3) {
      const rect = bbox(pts, pad + (m.type === 'cloud' ? 10 : 0));
      const filled = m.type === 'area' || m.type === 'volume' || m.type === 'dynamicFill';
      const fa = Math.max(0.1, Math.min(1, Number(m.fillAlpha ?? 0.3)));
      const ops = m.type === 'cloud'
        ? `${strokeHead}${cloudOps(pts, 7)}\nS`
        : filled
          ? `q /GS1 gs ${C.map(n2).join(' ')} rg ${pathOps(pts, true)} f Q\n${strokeHead}${pathOps(pts, true)}\nS`
          : `${strokeHead}${pathOps(pts, true)}\nS`;
      put({
        ...common,
        Subtype: 'Polygon',
        Rect: rect,
        Vertices: pts.flatMap((q) => [q.x, q.y]),
        ...(m.type === 'cloud' ? { BE: { S: 'C', I: 1 } } : {}),
        ...(filled ? { IC: C } : {}),
        AP: { N: apRef(doc, rect, ops, { CA, ca: filled ? fa : CA }) },
      });
      if (dim) {
        const cx = pts.reduce((a, q) => a + q.x, 0) / pts.length;
        const cy = pts.reduce((a, q) => a + q.y, 0) / pts.length;
        label(common, dim, { x: cx, y: cy }, C, 9, m.id);
      }
    } else if (OPEN.has(m.type) && pts.length >= 2) {
      const rect = bbox(pts, pad);
      put({ ...common, Subtype: 'PolyLine', Rect: rect, Vertices: pts.flatMap((q) => [q.x, q.y]), AP: { N: apRef(doc, rect, `${strokeHead}${pathOps(pts, false)}\nS`, { CA }) } });
      if (dim) {
        // On the longest segment, a little above it.
        let best = 0;
        let at = { x: pts[0]!.x, y: pts[0]!.y };
        for (let k = 0; k + 1 < pts.length; k++) {
          const a = pts[k]!;
          const b = pts[k + 1]!;
          const L = Math.hypot(b.x - a.x, b.y - a.y);
          if (L > best) { best = L; at = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 + 8 }; }
        }
        label(common, dim, at, C, 9, m.id);
      }
    } else if (LINES.has(m.type) && pts.length >= 2) {
      const a = pts[0]!;
      const b = pts[pts.length - 1]!;
      const rect = bbox([a, b], pad + 8);
      let ops = `${strokeHead}${n2(a.x)} ${n2(a.y)} m ${n2(b.x)} ${n2(b.y)} l S`;
      if (m.type === 'arrow') {
        const ang = Math.atan2(b.y - a.y, b.x - a.x);
        const hl = 9 + w;
        const p1 = { x: b.x - hl * Math.cos(ang - 0.45), y: b.y - hl * Math.sin(ang - 0.45) };
        const p2 = { x: b.x - hl * Math.cos(ang + 0.45), y: b.y - hl * Math.sin(ang + 0.45) };
        ops += `\n${C.map(n2).join(' ')} rg ${pathOps([b, p1, p2], true)} f`;
      }
      put({ ...common, Subtype: 'Line', Rect: rect, L: [a.x, a.y, b.x, b.y], ...(m.type === 'arrow' ? { LE: ['None', 'ClosedArrow'], IC: C } : {}), AP: { N: apRef(doc, rect, ops, { CA }) } });
      if (dim && m.type !== 'arrow') label(common, dim, { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 + 8 }, C, 9, m.id);
    } else if (BOXES.has(m.type) && pts.length >= 2) {
      const rect = bbox([pts[0]!, pts[pts.length - 1]!], 0);
      const hl = m.type === 'highlight';
      const hc = hl ? [1, 0.88, 0.28] : C;
      const ops = hl
        ? `${hc.map(n2).join(' ')} rg ${n2(rect[0]!)} ${n2(rect[1]!)} ${n2(rect[2]! - rect[0]!)} ${n2(rect[3]! - rect[1]!)} re f`
        : `${strokeHead}${n2(rect[0]! + w / 2)} ${n2(rect[1]! + w / 2)} ${n2(rect[2]! - rect[0]! - w)} ${n2(rect[3]! - rect[1]! - w)} re S`;
      put({ ...common, Subtype: 'Square', Rect: rect, ...(hl ? { IC: hc, C: hc, CA: 0.35 } : {}), AP: { N: apRef(doc, rect, ops, { CA: hl ? 0.35 : CA }) } });
      if (dim && (m.type as string) === 'rectarea') label(common, dim, { x: (rect[0]! + rect[2]!) / 2, y: (rect[1]! + rect[3]!) / 2 }, C, 9, m.id);
    } else if (m.type === 'ellipse' && pts.length >= 2) {
      const rect = bbox([pts[0]!, pts[pts.length - 1]!], 0);
      const cx = (rect[0]! + rect[2]!) / 2;
      const cy = (rect[1]! + rect[3]!) / 2;
      put({ ...common, Subtype: 'Circle', Rect: rect, AP: { N: apRef(doc, rect, `${strokeHead}${ellipseOps(cx, cy, (rect[2]! - rect[0]!) / 2 - w / 2, (rect[3]! - rect[1]!) / 2 - w / 2)} S`, { CA }) } });
    } else if (m.type === 'pen' && pts.length >= 2) {
      const rect = bbox(pts, pad);
      put({ ...common, Subtype: 'Ink', Rect: rect, InkList: [pts.flatMap((q) => [q.x, q.y])], AP: { N: apRef(doc, rect, `${strokeHead}${pathOps(pts, false)}\nS`, { CA }) } });
    } else if ((m.type === 'text' || m.type === 'callout' || m.type === 'stamp') && pts.length >= 1) {
      const anchor = m.type === 'callout' ? pts[1] ?? pts[0]! : pts[0]!;
      const wPt = Math.max(40, Number(m.width ?? 120));
      const hPt = Math.max(14, Number(m.height ?? 18));
      const box = [anchor.x, anchor.y - hPt, anchor.x + wPt, anchor.y];
      const txt = String(m.text ?? text ?? '');
      const lines = txt.split('\n');
      let rect = box;
      let ops = `1 1 1 rg ${n2(box[0]!)} ${n2(box[1]!)} ${n2(wPt)} ${n2(hPt)} re f\n${strokeHead}${n2(box[0]!)} ${n2(box[1]!)} ${n2(wPt)} ${n2(hPt)} re S`;
      if (m.type === 'callout' && pts[0]) {
        const tip = pts[0];
        const end = { x: Math.max(box[0]!, Math.min(tip.x, box[2]!)), y: Math.max(box[1]!, Math.min(tip.y, box[3]!)) };
        const ang = Math.atan2(tip.y - end.y, tip.x - end.x);
        const hl = 9;
        const p1 = { x: tip.x - hl * Math.cos(ang - 0.45), y: tip.y - hl * Math.sin(ang - 0.45) };
        const p2 = { x: tip.x - hl * Math.cos(ang + 0.45), y: tip.y - hl * Math.sin(ang + 0.45) };
        ops += `\n${n2(end.x)} ${n2(end.y)} m ${n2(tip.x)} ${n2(tip.y)} l S\n${C.map(n2).join(' ')} rg ${pathOps([tip, p1, p2], true)} f`;
        rect = [Math.min(box[0]!, tip.x) - 10, Math.min(box[1]!, tip.y) - 10, Math.max(box[2]!, tip.x) + 10, Math.max(box[3]!, tip.y) + 10];
      }
      const fs = 9;
      lines.forEach((ln, li) => {
        const t = ln.replace(/[^\x20-\x7E\u00A0-\u00FF]/g, '');
        if (t) ops += `\nBT /F1 ${fs} Tf ${C.map(n2).join(' ')} rg ${n2(box[0]! + 4)} ${n2(box[3]! - 4 - fs - li * fs * 1.3)} Td ${font.encodeText(t).toString()} Tj ET`;
      });
      put({
        ...common,
        Subtype: 'FreeText',
        Rect: rect,
        DA: PDFString.of(`/Helv ${fs} Tf ${C.map(n2).join(' ')} rg`),
        Contents: PDFHexString.fromText(txt),
        ...(m.type === 'callout' && pts[0] ? { CL: [pts[0].x, pts[0].y, anchor.x, anchor.y - hPt / 2], IT: 'FreeTextCallout', LE: 'OpenArrow' } : {}),
        AP: { N: apRef(doc, rect, ops, { CA, font }) },
      });
    }
  }
  return n;
}

/** Remove annotations an earlier ERP save wrote (NM "oe-..."), so a re-save
 *  never stacks copies. */
function dropOwnAnnots(doc: PDFDocument): void {
  for (const page of doc.getPages()) {
    const annots = page.node.lookupMaybe(PDFName.of('Annots'), PDFArray);
    if (!annots) continue;
    const keep = PDFArray.withContext(doc.context);
    for (let i = 0; i < annots.size(); i++) {
      const ref = annots.get(i);
      const d = doc.context.lookup(ref);
      let own = false;
      if (d && typeof (d as { get?: unknown }).get === 'function') {
        const nm = (d as unknown as { get: (k: PDFName) => unknown }).get(PDFName.of('NM'));
        const s = nm instanceof PDFString || nm instanceof PDFHexString ? nm.decodeText() : '';
        own = s.startsWith('oe-');
      }
      if (!own) keep.push(ref);
    }
    page.node.set(PDFName.of('Annots'), keep);
  }
}

/**
 * Revu-style Save PDF: the original file, every page, markups as PDF
 * annotations, plus the ERP snapshot (markups + page scales) so the ERP
 * reopens them editable.
 */
export async function saveVectorPdf(
  original: Uint8Array,
  byPage: Map<number, AnnotInput[]>,
  snapshot: TakeoffSnapshotV,
): Promise<{ bytes: Uint8Array; annots: number }> {
  const doc = await PDFDocument.load(original, { ignoreEncryption: true, updateMetadata: false });
  dropOwnAnnots(doc);
  const font = await doc.embedFont(StandardFonts.Helvetica);
  let annots = 0;
  for (const [page, items] of byPage) {
    if (page >= 1 && page <= doc.getPageCount()) annots += addAnnots(doc, page - 1, items, font);
  }
  setSnapshot(doc, snapshot);
  doc.setModificationDate(new Date());
  return { bytes: await doc.save(), annots };
}

/* ── Page tools ───────────────────────────────────────────────────── */

async function load(bytes: Uint8Array): Promise<PDFDocument> {
  return PDFDocument.load(bytes, { ignoreEncryption: true, updateMetadata: false });
}

/** A new PDF of the given pages (1-based, in order). */
export async function extractPages(bytes: Uint8Array, pages: number[]): Promise<Uint8Array> {
  const src = await load(bytes);
  const out = await PDFDocument.create();
  const copied = await out.copyPages(src, pages.map((p) => p - 1));
  copied.forEach((p) => out.addPage(p));
  return out.save();
}

export type PageEdit =
  | { kind: 'delete'; pages: number[] }
  | { kind: 'rotate'; pages: number[]; deg: 90 | 180 | 270 }
  | { kind: 'insertBlank'; after: number; count: number; size?: [number, number] }
  | { kind: 'insertPdf'; after: number; other: Uint8Array; otherPages?: number[] }
  | { kind: 'replace'; pages: number[]; other: Uint8Array; otherPages?: number[] }
  | { kind: 'repair' };

/**
 * Apply a page edit; returns the new bytes and where each original page went
 * (1-based; a deleted / replaced page is missing from the map).
 */
export async function editPages(bytes: Uint8Array, edit: PageEdit): Promise<{ bytes: Uint8Array; pageMap: Record<number, number>; numPages: number }> {
  const src = await load(bytes);
  const n = src.getPageCount();
  const map: Record<number, number> = {};
  if (edit.kind === 'repair') {
    for (let i = 1; i <= n; i++) map[i] = i;
    return { bytes: await src.save({ useObjectStreams: true }), pageMap: map, numPages: n };
  }
  if (edit.kind === 'rotate') {
    for (const p of edit.pages) {
      const pg = src.getPage(p - 1);
      pg.setRotation(degrees(((pg.getRotation().angle + edit.deg) % 360 + 360) % 360));
    }
    for (let i = 1; i <= n; i++) map[i] = i;
    return { bytes: await src.save(), pageMap: map, numPages: n };
  }
  // Rebuild the page order.
  const out = await PDFDocument.create();
  // Keep the document info (title, keywords are re-set by the caller).
  const plan: ({ from: 'src'; i: number } | { from: 'blank'; size: [number, number] } | { from: 'other'; i: number })[] = [];
  let other: PDFDocument | null = null;
  if (edit.kind === 'insertPdf' || edit.kind === 'replace') other = await load(edit.other);
  const otherList = other ? (('otherPages' in edit && edit.otherPages?.length ? edit.otherPages : Array.from({ length: other.getPageCount() }, (_, i) => i + 1))) : [];
  const del = new Set(edit.kind === 'delete' ? edit.pages : []);
  const rep = new Set(edit.kind === 'replace' ? edit.pages : []);
  let otherCursor = 0;
  if ((edit.kind === 'insertBlank' || edit.kind === 'insertPdf') && edit.after === 0) {
    if (edit.kind === 'insertBlank') for (let k = 0; k < edit.count; k++) plan.push({ from: 'blank', size: edit.size ?? sizeOf(src, 0) });
    else otherList.forEach((op) => plan.push({ from: 'other', i: op - 1 }));
  }
  for (let i = 1; i <= n; i++) {
    if (del.has(i)) continue;
    if (rep.has(i)) {
      const op = otherList[otherCursor++];
      if (op !== undefined) plan.push({ from: 'other', i: op - 1 });
      continue;
    }
    plan.push({ from: 'src', i: i - 1 });
    map[i] = plan.length;
    if ((edit.kind === 'insertBlank' || edit.kind === 'insertPdf') && edit.after === i) {
      if (edit.kind === 'insertBlank') for (let k = 0; k < edit.count; k++) plan.push({ from: 'blank', size: edit.size ?? sizeOf(src, i - 1) });
      else otherList.forEach((op) => plan.push({ from: 'other', i: op - 1 }));
    }
  }
  const srcIdx = plan.filter((x) => x.from === 'src').map((x) => (x as { i: number }).i);
  const srcCopies = await out.copyPages(src, srcIdx);
  const otherIdx = plan.filter((x) => x.from === 'other').map((x) => (x as { i: number }).i);
  const otherCopies = other && otherIdx.length ? await out.copyPages(other, otherIdx) : [];
  let si = 0;
  let oi = 0;
  for (const step of plan) {
    if (step.from === 'src') out.addPage(srcCopies[si++]!);
    else if (step.from === 'other') out.addPage(otherCopies[oi++]!);
    else out.addPage(step.size);
  }
  return { bytes: await out.save(), pageMap: map, numPages: plan.length };
}

function sizeOf(doc: PDFDocument, idx: number): [number, number] {
  const p = doc.getPage(Math.max(0, Math.min(idx, doc.getPageCount() - 1)));
  const { width, height } = p.getSize();
  return [width, height];
}

/** Write (or clear) the ERP snapshot on finished bytes. */
export async function withSnapshot(bytes: Uint8Array, snap: TakeoffSnapshotV | null): Promise<Uint8Array> {
  const doc = await load(bytes);
  setSnapshot(doc, snap);
  return doc.save();
}

/** Page count of a PDF. */
export async function pageCountOf(bytes: Uint8Array): Promise<number> {
  return (await load(bytes)).getPageCount();
}

/** Rotate viewport-space points with the page (scale 1 viewport w x h). */
export function rotatePoint(p: Pt, deg: 90 | 180 | 270, w: number, h: number): Pt {
  if (deg === 90) return { x: h - p.y, y: p.x };
  if (deg === 180) return { x: w - p.x, y: h - p.y };
  return { x: p.y, y: w - p.x };
}

void PDFNumber;

/* ── Combine + new PDF (update 21) ─────────────────────────────────── */

/** Join PDFs in order; returns the bytes and where each part's page 1 landed (0-based offset). */
export async function combinePdfs(parts: Uint8Array[]): Promise<{ bytes: Uint8Array; offsets: number[]; numPages: number }> {
  const out = await PDFDocument.create();
  const offsets: number[] = [];
  for (const b of parts) {
    const src = await load(b);
    offsets.push(out.getPageCount());
    const copied = await out.copyPages(src, src.getPageIndices());
    copied.forEach((p) => out.addPage(p));
  }
  return { bytes: await out.save(), offsets, numPages: out.getPageCount() };
}

/** A new blank PDF: `count` pages of width x height PDF points. */
export async function createBlankPdf(widthPt: number, heightPt: number, count: number, title?: string): Promise<Uint8Array> {
  const d = await PDFDocument.create();
  for (let i = 0; i < Math.max(1, Math.min(500, Math.round(count))); i++) d.addPage([widthPt, heightPt]);
  if (title) d.setTitle(title);
  return d.save();
}
