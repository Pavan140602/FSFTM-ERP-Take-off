# OE-DELIVERY: 2026-10-30-detect-viewer-patch2
"""Upgrade the Detect overlay: draw the member's LINE, rotate its label.

Run once from the repo root, AFTER patch_viewer_detect.py:

    python patch_viewer_detect2.py

The pilot overlay only boxed the printed label. Estimators read a
framing plan by its lines, so now (detect.py v2 attaches each label
to the member line it names):

  * the member line itself is stroked on the sheet (soft halo +
    solid core, coloured by status: blue confirmed, amber verify,
    orange selected);
  * the profile/length chip sits beside the line at the printed
    label's position and is ROTATED to the line's angle — horizontal
    text on horizontal members, vertical text on vertical members,
    angled text on sloped members, never upside down;
  * marks with no line (schedule-only rows, hand-added rows) keep
    the pilot's box + chip rendering.

Anchor-verified + idempotent: anchors are checked BEFORE anything
is written; on any mismatch the file is left untouched. A
.bak-detect2 copy is written first. Hard-refresh afterwards.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

TARGET = Path("frontend/src/modules/pdf-takeoff/TakeoffViewerModule.tsx")

ALREADY_MARKER = "the member's own line drawn on"

STATE_OLD = "const [detectMarks, setDetectMarks] = useState<{ id: string; page: number; rect: number[]; label: string; status: 'confirmed' | 'verify' | 'selected' }[]>([]);"
STATE_NEW = "const [detectMarks, setDetectMarks] = useState<{ id: string; page: number; rect: number[]; label: string; status: 'confirmed' | 'verify' | 'selected'; line: number[] | null; angle: number | null }[]>([]);"

SPAN_START = "                {/* Detect marks overlay"

NEW_BLOCK = """                {/* Detect marks overlay — the member's own line drawn on
                    the sheet, with the profile/length label rotated to
                    the line's angle. Blue = confirmed, amber = to verify,
                    orange = selected in the panel. Marks without a line
                    (schedule-only, added by hand) keep a box + chip. */}
                {detectMarks.some((m) => m.page === currentPage) && (
                  <svg
                    className="pointer-events-none absolute left-0"
                    style={{ top: overlayTop, zIndex: 6, width: '100%', height: '100%' }}
                    width="100%"
                    height="100%"
                  >
                    {detectMarks.filter((m) => m.page === currentPage).map((m) => {
                      const color = m.status === 'selected' ? '#EA580C' : m.status === 'verify' ? '#D97706' : '#2563EB';
                      const chipW = m.label.length * 6.4 + 10;
                      if (m.line && m.line.length === 4) {
                        const lx1 = m.line[0]! * zoom;
                        const ly1 = m.line[1]! * zoom;
                        const lx2 = m.line[2]! * zoom;
                        const ly2 = m.line[3]! * zoom;
                        const rcx = ((m.rect[0]! + m.rect[2]!) / 2) * zoom;
                        const rcy = ((m.rect[1]! + m.rect[3]!) / 2) * zoom;
                        const dx = lx2 - lx1;
                        const dy = ly2 - ly1;
                        const len = Math.hypot(dx, dy) || 1;
                        const t = Math.max(0, Math.min(1, ((rcx - lx1) * dx + (rcy - ly1) * dy) / (len * len)));
                        const ax = lx1 + t * dx;
                        const ay = ly1 + t * dy;
                        let nx = -dy / len;
                        let ny = dx / len;
                        if ((rcx - ax) * nx + (rcy - ay) * ny < 0) { nx = -nx; ny = -ny; }
                        const labelX = ax + nx * 12;
                        const labelY = ay + ny * 12;
                        const angle = m.angle ?? 0;
                        return (
                          <g key={m.id}>
                            <line x1={lx1} y1={ly1} x2={lx2} y2={ly2} stroke={color} strokeWidth={7} opacity={0.16} strokeLinecap="round" />
                            <line x1={lx1} y1={ly1} x2={lx2} y2={ly2} stroke={color} strokeWidth={m.status === 'selected' ? 3.5 : 2.5} opacity={0.95} strokeLinecap="round" />
                            <g transform={`translate(${labelX} ${labelY}) rotate(${angle})`}>
                              <rect x={-chipW / 2} y={-7.5} width={chipW} height={15} rx={3} fill={color} />
                              <text x={0} y={4} textAnchor="middle" fontSize={10} fontWeight={700} fill="#fff">{m.label}</text>
                            </g>
                          </g>
                        );
                      }
                      const x = m.rect[0]! * zoom;
                      const y = m.rect[1]! * zoom;
                      const w = Math.max((m.rect[2]! - m.rect[0]!) * zoom, 6);
                      const h = Math.max((m.rect[3]! - m.rect[1]!) * zoom, 6);
                      const chipY = y >= 20 ? y - 18 : y + h + 3;
                      return (
                        <g key={m.id}>
                          <rect x={x} y={y} width={w} height={h} fill={color} opacity={0.14} stroke={color} strokeWidth={m.status === 'selected' ? 2.5 : 1.5} />
                          <rect x={x} y={chipY} width={chipW} height={15} rx={3} fill={color} />
                          <text x={x + 5} y={chipY + 11} fontSize={10} fontWeight={700} fill="#fff">{m.label}</text>
                        </g>
                      );
                    })}
                  </svg>
                )}"""


def main() -> int:
    if not TARGET.exists():
        print(f"TARGET MISSING: {TARGET} (run from the repo root)")
        return 1
    text = TARGET.read_text(encoding="utf-8")
    if ALREADY_MARKER in text:
        print("Already applied: line overlay present, nothing changed.")
        return 0
    if text.count(STATE_OLD) != 1:
        print("ANCHOR MISSING: detectMarks state (v1 form) — apply patch_viewer_detect.py first. Nothing changed.")
        return 1
    start = text.find(SPAN_START)
    if start < 0:
        print("ANCHOR MISSING: v1 detect overlay block not found. Nothing changed.")
        return 1
    end_marker = "                  </svg>\n                )}"
    end = text.find(end_marker, start)
    if end < 0:
        print("ANCHOR MISSING: v1 detect overlay closing not found. Nothing changed.")
        return 1
    end += len(end_marker)
    backup = TARGET.with_suffix(".tsx.bak-detect2")
    shutil.copy2(TARGET, backup)
    text = text.replace(STATE_OLD, STATE_NEW, 1)
    start = text.find(SPAN_START)
    end = text.find(end_marker, start) + len(end_marker)
    text = text[:start] + NEW_BLOCK + text[end:]
    TARGET.write_text(text, encoding="utf-8")
    print(f"Patched OK: {TARGET} (backup: {backup})")
    print("Hard-refresh the browser (Ctrl+Shift+R) to load the line overlay.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
