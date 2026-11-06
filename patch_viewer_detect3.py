# OE-DELIVERY: 2026-10-30-viewer-detect3
"""Viewer patch 3 for the Detect feature: interactive drawing marks.

Run AFTER patch_viewer_detect.py and patch_viewer_detect2.py:
    python patch_viewer_detect3.py          (from the repo root)

What changes in TakeoffViewerModule.tsx:
  1. The detect marks state gains category + lengthFt (the panel
     sends them; the viewer colours each line by its category).
  2. New pick-mode state + helpers + listeners: the Detect panel
     toggles pick mode via an 'oe-detect:pickmode' window event;
     Esc on the drawing exits it.
  3. The overlay becomes interactive in pick mode: lines are drawn
     in category colours (solid = verified, dashed = to verify,
     white outline = selected); clicking a line selects it and
     opens its panel row; dragging on empty sheet marquee-selects
     every line it touches; a lone selected line shows end handles
     and dragging an end resizes the line along its own axis,
     updating its length live. Interactions are reported to the
     panel ('oe-detect:toggle' / 'oe-detect:marquee' /
     'oe-detect:linedrag'), which owns rows + selection + saving.

Idempotent: re-running after a successful patch is a no-op.
A backup is written to TakeoffViewerModule.tsx.bak-detect3.
"""
from pathlib import Path

TARGET = Path("frontend/src/modules/pdf-takeoff/TakeoffViewerModule.tsx")
BACKUP = TARGET.with_suffix(".tsx.bak-detect3")
ALREADY_MARKER = "oe-detect:linedrag"

STATE_OLD = "const [detectMarks, setDetectMarks] = useState<{ id: string; page: number; rect: number[]; label: string; status: 'confirmed' | 'verify' | 'selected'; line: number[] | null; angle: number | null }[]>([]);"

STATE_NEW = """const [detectMarks, setDetectMarks] = useState<{ id: string; page: number; rect: number[]; label: string; status: 'confirmed' | 'verify' | 'selected'; category: string; line: number[] | null; angle: number | null; lengthFt: number | null }[]>([]);
  const [detectPickMode, setDetectPickMode] = useState(false);
  const [detectDrag, setDetectDrag] = useState<{ kind: 'click' | 'marquee' | 'end'; id?: string; end?: number; startX: number; startY: number; additive: boolean } | null>(null);
  const [detectMarquee, setDetectMarquee] = useState<{ x0: number; y0: number; x1: number; y1: number } | null>(null);
  const [detectDragLine, setDetectDragLine] = useState<{ id: string; line: number[] } | null>(null);
  const DETECT_CATEGORY_COLORS: Record<string, string> = { beams: '#3B82F6', columns: '#A855F7', joists: '#F97316', studs: '#14B8A6', walls: '#EC4899', trusses: '#EF4444', area: '#22C55E', other: '#9CA3AF' };
  useEffect(() => {
    const onPick = (e: Event) => {
      const d = (e as CustomEvent).detail as { on?: boolean } | undefined;
      setDetectPickMode(Boolean(d?.on));
    };
    window.addEventListener('oe-detect:pickmode', onPick);
    return () => window.removeEventListener('oe-detect:pickmode', onPick);
  }, []);
  useEffect(() => {
    if (!detectPickMode) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setDetectPickMode(false);
        window.dispatchEvent(new CustomEvent('oe-detect:pickmode', { detail: { on: false, fromViewer: true } }));
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [detectPickMode]);
  const detectEvtPos = (e: any) => {
    const r = (e.currentTarget as SVGSVGElement).getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  };
  const detectFmtLen = (ft: number) => {
    const totalIn = Math.round(ft * 12);
    return `${Math.floor(totalIn / 12)}'-${totalIn % 12}"`;
  };
  const detectSegSeg = (ax: number, ay: number, bx: number, by: number, cx: number, cy: number, dx: number, dy: number) => {
    const o1 = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax);
    const o2 = (bx - ax) * (dy - ay) - (by - ay) * (dx - ax);
    const o3 = (dx - cx) * (ay - cy) - (dy - cy) * (ax - cx);
    const o4 = (dx - cx) * (by - cy) - (dy - cy) * (bx - cx);
    return o1 * o2 < 0 && o3 * o4 < 0;
  };
  const detectSegHitsRect = (x1: number, y1: number, x2: number, y2: number, rx0: number, ry0: number, rx1: number, ry1: number) => {
    const inside = (x: number, y: number) => x >= rx0 && x <= rx1 && y >= ry0 && y <= ry1;
    if (inside(x1, y1) || inside(x2, y2)) return true;
    return (
      detectSegSeg(x1, y1, x2, y2, rx0, ry0, rx1, ry0) ||
      detectSegSeg(x1, y1, x2, y2, rx1, ry0, rx1, ry1) ||
      detectSegSeg(x1, y1, x2, y2, rx1, ry1, rx0, ry1) ||
      detectSegSeg(x1, y1, x2, y2, rx0, ry1, rx0, ry0)
    );
  };
  const detectMarkHitsRect = (m: { rect: number[]; line: number[] | null }, rx0: number, ry0: number, rx1: number, ry1: number) => {
    if (m.line && m.line.length === 4) {
      return detectSegHitsRect(m.line[0] * zoom, m.line[1] * zoom, m.line[2] * zoom, m.line[3] * zoom, rx0, ry0, rx1, ry1);
    }
    const [bx, by, bx2, by2] = m.rect;
    return !(bx2 * zoom < rx0 || bx * zoom > rx1 || by2 * zoom < ry0 || by * zoom > ry1);
  };"""

SPAN_START = "                {/* Detect marks overlay"
SPAN_END = "                  </svg>\n                )}"

NEW_BLOCK = """                {/* Detect marks overlay — category-coloured member lines:
                    solid = verified, dashed = to verify, white outline =
                    selected. In pick mode (Detect panel toggle) a line can
                    be clicked to select/edit it, a drag on empty sheet
                    marquee-selects the lines it touches, and a lone
                    selected line's ends can be dragged to resize it with
                    the length updating live; the overlay reports all of
                    it back to the panel via window events. */}
                {detectMarks.some((m) => m.page === currentPage) && (
                  <svg
                    className="absolute left-0"
                    style={{ top: overlayTop, zIndex: 6, width: '100%', height: '100%', pointerEvents: detectPickMode ? 'auto' : 'none' }}
                    onPointerDown={(e) => {
                      if (!detectPickMode) return;
                      e.stopPropagation();
                      e.preventDefault();
                      const pos = detectEvtPos(e);
                      const tgt = e.target as SVGElement;
                      const markId = tgt.getAttribute('data-detect-id');
                      const endAttr = tgt.getAttribute('data-detect-end');
                      const additive = e.shiftKey || e.ctrlKey || e.metaKey;
                      (e.currentTarget as SVGSVGElement).setPointerCapture(e.pointerId);
                      if (markId && endAttr) {
                        const mark = detectMarks.find((x) => x.id === markId);
                        if (mark?.line) {
                          setDetectDrag({ kind: 'end', id: markId, end: Number(endAttr), startX: pos.x, startY: pos.y, additive });
                          setDetectDragLine({ id: markId, line: mark.line });
                        }
                      } else if (markId) {
                        setDetectDrag({ kind: 'click', id: markId, startX: pos.x, startY: pos.y, additive });
                      } else {
                        setDetectDrag({ kind: 'marquee', startX: pos.x, startY: pos.y, additive });
                        setDetectMarquee({ x0: pos.x, y0: pos.y, x1: pos.x, y1: pos.y });
                      }
                    }}
                    onPointerMove={(e) => {
                      if (!detectDrag) return;
                      e.stopPropagation();
                      const pos = detectEvtPos(e);
                      if (detectDrag.kind === 'marquee') {
                        setDetectMarquee({ x0: detectDrag.startX, y0: detectDrag.startY, x1: pos.x, y1: pos.y });
                        return;
                      }
                      if (detectDrag.kind === 'end' && detectDrag.id) {
                        const mark = detectMarks.find((x) => x.id === detectDrag.id);
                        if (!mark?.line) return;
                        const [lx1, ly1, lx2, ly2] = mark.line;
                        const fixed: [number, number] = detectDrag.end === 0 ? [lx2, ly2] : [lx1, ly1];
                        let ax = (detectDrag.end === 0 ? lx1 - lx2 : lx2 - lx1);
                        let ay = (detectDrag.end === 0 ? ly1 - ly2 : ly2 - ly1);
                        const alen = Math.hypot(ax, ay) || 1;
                        ax /= alen;
                        ay /= alen;
                        const px = pos.x / zoom;
                        const py = pos.y / zoom;
                        const t = Math.max(12, (px - fixed[0]) * ax + (py - fixed[1]) * ay);
                        const nx = fixed[0] + ax * t;
                        const ny = fixed[1] + ay * t;
                        setDetectDragLine({ id: mark.id, line: detectDrag.end === 0 ? [nx, ny, lx2, ly2] : [lx1, ly1, nx, ny] });
                      }
                    }}
                    onPointerUp={(e) => {
                      if (!detectDrag) return;
                      e.stopPropagation();
                      const pos = detectEvtPos(e);
                      if (detectDrag.kind === 'click' && detectDrag.id) {
                        if (Math.hypot(pos.x - detectDrag.startX, pos.y - detectDrag.startY) < 5) {
                          window.dispatchEvent(new CustomEvent('oe-detect:toggle', { detail: { id: detectDrag.id, additive: detectDrag.additive, focus: !detectDrag.additive } }));
                        }
                      } else if (detectDrag.kind === 'marquee' && detectMarquee) {
                        const rx0 = Math.min(detectMarquee.x0, detectMarquee.x1);
                        const ry0 = Math.min(detectMarquee.y0, detectMarquee.y1);
                        const rx1 = Math.max(detectMarquee.x0, detectMarquee.x1);
                        const ry1 = Math.max(detectMarquee.y0, detectMarquee.y1);
                        if (rx1 - rx0 > 4 || ry1 - ry0 > 4) {
                          const ids = detectMarks
                            .filter((m) => m.page === currentPage && detectMarkHitsRect(m, rx0, ry0, rx1, ry1))
                            .map((m) => m.id);
                          window.dispatchEvent(new CustomEvent('oe-detect:marquee', { detail: { ids, additive: detectDrag.additive } }));
                        }
                        setDetectMarquee(null);
                      } else if (detectDrag.kind === 'end' && detectDrag.id && detectDragLine) {
                        window.dispatchEvent(new CustomEvent('oe-detect:linedrag', { detail: { id: detectDrag.id, line: detectDragLine.line } }));
                        setDetectDragLine(null);
                      }
                      setDetectDrag(null);
                    }}
                  >
                    {detectPickMode && <rect x={0} y={0} width="100%" height="100%" fill="transparent" />}
                    {detectMarks
                      .filter((m) => m.page === currentPage)
                      .map((m) => {
                        const color = DETECT_CATEGORY_COLORS[m.category] ?? '#9CA3AF';
                        const selected = m.status === 'selected';
                        const dash = m.status === 'verify' ? '7 5' : undefined;
                        const dragLine = detectDragLine && detectDragLine.id === m.id ? detectDragLine.line : null;
                        let chipText = m.label;
                        if (dragLine && m.line && m.lengthFt) {
                          const oldRun = Math.hypot(m.line[2] - m.line[0], m.line[3] - m.line[1]);
                          const newRun = Math.hypot(dragLine[2] - dragLine[0], dragLine[3] - dragLine[1]);
                          if (oldRun > 0) chipText = `${m.label.split(' · ')[0]} · ${detectFmtLen((m.lengthFt * newRun) / oldRun)}`;
                        }
                        const chipW = Math.max(34, chipText.length * 6.4 + 10);
                        if (m.line && m.line.length === 4) {
                          const line = dragLine ?? m.line;
                          const [lx1, ly1, lx2, ly2] = line;
                          const rawAngle = (Math.atan2(ly2 - ly1, lx2 - lx1) * 180) / Math.PI;
                          const angle = dragLine ? (((rawAngle + 90) % 180) + 180) % 180 - 90 : m.angle ?? rawAngle;
                          const cx = (m.rect[0] + m.rect[2]) / 2;
                          const cy = (m.rect[1] + m.rect[3]) / 2;
                          const dx = lx2 - lx1;
                          const dy = ly2 - ly1;
                          const segLen2 = dx * dx + dy * dy || 1;
                          const tt = Math.max(0, Math.min(1, ((cx - lx1) * dx + (cy - ly1) * dy) / segLen2));
                          const px = lx1 + tt * dx;
                          const py = ly1 + tt * dy;
                          const segLen = Math.sqrt(segLen2);
                          let nx = -dy / segLen;
                          let ny = dx / segLen;
                          if ((cx - px) * nx + (cy - py) * ny < 0) {
                            nx = -nx;
                            ny = -ny;
                          }
                          const off = 12 / zoom;
                          const labelX = (px + nx * off) * zoom;
                          const labelY = (py + ny * off) * zoom;
                          return (
                            <g key={m.id}>
                              {selected ? (
                                <line x1={lx1 * zoom} y1={ly1 * zoom} x2={lx2 * zoom} y2={ly2 * zoom} stroke="#FFFFFF" strokeWidth={9} strokeLinecap="round" opacity={0.9} pointerEvents="none" />
                              ) : (
                                <line x1={lx1 * zoom} y1={ly1 * zoom} x2={lx2 * zoom} y2={ly2 * zoom} stroke={color} strokeWidth={7} strokeLinecap="round" opacity={0.16} pointerEvents="none" />
                              )}
                              <line x1={lx1 * zoom} y1={ly1 * zoom} x2={lx2 * zoom} y2={ly2 * zoom} stroke={color} strokeWidth={selected ? 3.5 : 2.5} strokeLinecap="round" strokeDasharray={dash} pointerEvents="none" />
                              {detectPickMode && (
                                <line x1={lx1 * zoom} y1={ly1 * zoom} x2={lx2 * zoom} y2={ly2 * zoom} stroke="transparent" strokeWidth={14} data-detect-id={m.id} style={{ cursor: 'pointer' }} />
                              )}
                              <g transform={`translate(${labelX} ${labelY}) rotate(${angle})`} pointerEvents="none">
                                <rect x={-chipW / 2} y={-8} width={chipW} height={16} rx={3} fill={color} stroke={selected ? '#FFFFFF' : 'none'} strokeWidth={selected ? 1.5 : 0} />
                                <text x={0} y={3.5} textAnchor="middle" fontSize={10.5} fontWeight={600} fill="#FFFFFF">
                                  {chipText}
                                </text>
                              </g>
                            </g>
                          );
                        }
                        const [bx, by, bx2, by2] = m.rect;
                        const chipY = by * zoom - 8;
                        return (
                          <g key={m.id}>
                            <rect x={bx * zoom} y={by * zoom} width={(bx2 - bx) * zoom} height={(by2 - by) * zoom} fill={color} fillOpacity={0.14} stroke={selected ? '#FFFFFF' : color} strokeWidth={selected ? 2 : 1.2} strokeDasharray={dash} pointerEvents="none" />
                            {detectPickMode && (
                              <rect x={bx * zoom} y={by * zoom} width={(bx2 - bx) * zoom} height={(by2 - by) * zoom} fill="transparent" data-detect-id={m.id} style={{ cursor: 'pointer' }} />
                            )}
                            <g pointerEvents="none">
                              <rect x={(bx + bx2) / 2 * zoom - chipW / 2} y={chipY - 8} width={chipW} height={16} rx={3} fill={color} stroke={selected ? '#FFFFFF' : 'none'} strokeWidth={selected ? 1.5 : 0} />
                              <text x={(bx + bx2) / 2 * zoom} y={chipY + 3.5} textAnchor="middle" fontSize={10.5} fontWeight={600} fill="#FFFFFF">
                                {chipText}
                              </text>
                            </g>
                          </g>
                        );
                      })}
                    {(() => {
                      const sel = detectMarks.filter((x) => x.page === currentPage && x.status === 'selected');
                      if (sel.length !== 1 || !sel[0].line) return null;
                      const m = sel[0];
                      const line = detectDragLine && detectDragLine.id === m.id ? detectDragLine.line : m.line;
                      if (!line) return null;
                      const color = DETECT_CATEGORY_COLORS[m.category] ?? '#9CA3AF';
                      return ([0, 1] as const).map((end) => (
                        <circle
                          key={end}
                          cx={line[end === 0 ? 0 : 2] * zoom}
                          cy={line[end === 0 ? 1 : 3] * zoom}
                          r={6}
                          fill="#FFFFFF"
                          stroke={color}
                          strokeWidth={2.5}
                          data-detect-id={m.id}
                          data-detect-end={end}
                          style={{ cursor: 'grab', pointerEvents: detectPickMode ? 'all' : 'none' }}
                        />
                      ));
                    })()}
                    {detectMarquee && (
                      <rect
                        x={Math.min(detectMarquee.x0, detectMarquee.x1)}
                        y={Math.min(detectMarquee.y0, detectMarquee.y1)}
                        width={Math.abs(detectMarquee.x1 - detectMarquee.x0)}
                        height={Math.abs(detectMarquee.y1 - detectMarquee.y0)}
                        fill="#FFFFFF"
                        fillOpacity={0.10}
                        stroke="#111827"
                        strokeWidth={1.2}
                        strokeDasharray="5 4"
                        pointerEvents="none"
                      />
                    )}
                  </svg>
                )}"""



def main() -> None:
    if not TARGET.exists():
        raise SystemExit(f"Target not found: {TARGET} — run this from the repo root.")
    text = TARGET.read_text(encoding="utf-8")
    before_lines = text.count("\n") + 1
    if ALREADY_MARKER in text:
        print("Already patched (detect overlay v3 present). Nothing to do.")
        return
    if text.count(STATE_OLD) != 1:
        raise SystemExit(
            "Expected the detect v2 marks state exactly once — was patch_viewer_detect2.py run? "
            f"(found {text.count(STATE_OLD)}). Nothing was written."
        )
    if SPAN_START not in text:
        raise SystemExit("Detect overlay block not found. Nothing was written.")
    start = text.find(SPAN_START)
    end = text.find(SPAN_END, start)
    if end == -1:
        raise SystemExit("Detect overlay block end not found. Nothing was written.")
    end += len(SPAN_END)

    BACKUP.write_text(text, encoding="utf-8")
    text = text.replace(STATE_OLD, STATE_NEW, 1)
    start = text.find(SPAN_START)
    end = text.find(SPAN_END, start) + len(SPAN_END)
    text = text[:start] + NEW_BLOCK + text[end:]
    TARGET.write_text(text, encoding="utf-8")
    after_lines = text.count("\n") + 1
    print(f"Patched OK. Backup: {BACKUP}")
    print(f"TakeoffViewerModule.tsx: {before_lines} -> {after_lines} lines.")


if __name__ == "__main__":
    main()
