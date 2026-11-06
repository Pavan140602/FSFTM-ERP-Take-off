# OE-DELIVERY: 2026-10-29-detect-viewer-patch
"""Add the Detect tab to the PDF Measurements right panel.

Run once from the repo root (the sibling file
frontend/src/modules/pdf-takeoff/DetectPanel.tsx must be in place
first, and the doc-intel + highlight patches from 2026-10-28/29 must
already be applied):

    python patch_viewer_detect.py

Changes (6 small insertions, no existing logic touched):
  1. Import DetectPanel next to AiAssistantPanel.
  2. sidebarTab gains the 'detect' value.
  3. detectMarks state — the boxes + profile/length labels the panel
     pushes up for the drawing overlay.
  4. A pointer-events-none SVG overlay over the sheet (same pattern
     as the multiply/offset ghost overlays) drawing the current
     page's detect marks: blue = confirmed, amber = verify,
     orange = selected in the panel.
  5. "Detect" tab button next to "AI Assistant".
  6. The DetectPanel element, wired to the same page-jump and
     highlight bridge as the AI panel, plus onShowMarks.

Anchor-verified + idempotent: every anchor is counted BEFORE
anything is written; on any mismatch the file is left untouched.
A .bak-detect copy is written first. Hard-refresh afterwards.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

TARGET = Path("frontend/src/modules/pdf-takeoff/TakeoffViewerModule.tsx")

ANCHOR_IMPORT = "import AiAssistantPanel from './AiAssistantPanel';"
AFTER_IMPORT = ANCHOR_IMPORT + "\nimport DetectPanel from './DetectPanel';"

ANCHOR_TAB_TYPE = "useState<'properties' | 'tools' | 'colours' | 'ai'>"
NEW_TAB_TYPE = "useState<'properties' | 'tools' | 'colours' | 'ai' | 'detect'>"

ANCHOR_SEARCH_STATE = "const [searchMatches, setSearchMatches] = useState<TextMatch[]>([]);"
AFTER_SEARCH_STATE = ANCHOR_SEARCH_STATE + """
  // Detect tab marks: boxes + profile/length labels pushed up by the
  // DetectPanel and drawn by the SVG overlay over the sheet.
  const [detectMarks, setDetectMarks] = useState<{ id: string; page: number; rect: number[]; label: string; status: 'confirmed' | 'verify' | 'selected' }[]>([]);"""

ANCHOR_OFFSET_GHOST = "{/* SVG overlay for the offset ghost preview — orange dashed. */}"
DETECT_OVERLAY = """                {/* Detect marks overlay — boxes + profile/length labels for
                    the Detect tab's results on this page. Blue = confirmed,
                    amber = to verify, orange = selected in the panel. */}
                {detectMarks.some((m) => m.page === currentPage) && (
                  <svg
                    className="pointer-events-none absolute left-0"
                    style={{ top: overlayTop, zIndex: 6, width: '100%', height: '100%' }}
                    width="100%"
                    height="100%"
                  >
                    {detectMarks.filter((m) => m.page === currentPage).map((m) => {
                      const x = m.rect[0]! * zoom;
                      const y = m.rect[1]! * zoom;
                      const w = Math.max((m.rect[2]! - m.rect[0]!) * zoom, 6);
                      const h = Math.max((m.rect[3]! - m.rect[1]!) * zoom, 6);
                      const color = m.status === 'selected' ? '#EA580C' : m.status === 'verify' ? '#D97706' : '#2563EB';
                      const chipW = m.label.length * 6.4 + 10;
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
                )}

"""

ANCHOR_AI_TAB_END = """                {t('takeoff_viewer.tab_ai', { defaultValue: 'AI Assistant' })}
              </button>
            </div>"""
NEW_AI_TAB_END = """                {t('takeoff_viewer.tab_ai', { defaultValue: 'AI Assistant' })}
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={sidebarTab === 'detect'}
                onClick={() => setSidebarTab('detect')}
                className={clsx(
                  'flex-1 px-2 py-1 rounded text-[11px] font-semibold transition-colors',
                  sidebarTab === 'detect'
                    ? 'bg-oe-blue text-white shadow-sm'
                    : 'text-content-secondary hover:bg-surface-secondary',
                )}
                data-testid="sidebar-tab-detect"
              >
                {t('takeoff_viewer.tab_detect', { defaultValue: 'Detect' })}
              </button>
            </div>"""

ANCHOR_AI_PANEL = """            {sidebarTab === 'ai' && (
              <AiAssistantPanel
                documentId={documentId}
                currentPage={currentPage}
                onJumpToPage={goToPage}
                onHighlightTerm={handlePanelHighlight}
                onClearHighlight={clearPanelHighlight}
              />
            )}"""
AFTER_AI_PANEL = ANCHOR_AI_PANEL + """

            {/* Detect — auto member detection with on-sheet marks. */}
            {sidebarTab === 'detect' && (
              <DetectPanel
                documentId={documentId}
                currentPage={currentPage}
                onJumpToPage={goToPage}
                onHighlightTerm={handlePanelHighlight}
                onClearHighlight={clearPanelHighlight}
                onShowMarks={setDetectMarks}
              />
            )}"""

REPLACEMENTS = (
    ("panel import", ANCHOR_IMPORT, AFTER_IMPORT),
    ("sidebarTab type", ANCHOR_TAB_TYPE, NEW_TAB_TYPE),
    ("detect marks state", ANCHOR_SEARCH_STATE, AFTER_SEARCH_STATE),
    ("detect overlay", ANCHOR_OFFSET_GHOST, DETECT_OVERLAY + ANCHOR_OFFSET_GHOST),
    ("detect tab button", ANCHOR_AI_TAB_END, NEW_AI_TAB_END),
    ("detect panel element", ANCHOR_AI_PANEL, AFTER_AI_PANEL),
)


def main() -> int:
    if not TARGET.exists():
        print(f"TARGET MISSING: {TARGET} (run from the repo root)")
        return 1
    text = TARGET.read_text(encoding="utf-8")
    if "DetectPanel" in text and "sidebar-tab-detect" in text:
        print("Already applied: Detect tab present, nothing changed.")
        return 0
    missing = [name for name, anchor, _new in REPLACEMENTS if text.count(anchor) != 1]
    if missing:
        print(f"ANCHOR(S) MISSING OR NOT UNIQUE: {', '.join(missing)} — nothing changed.")
        print("This patch expects the doc-intel + highlight viewer (18,162 lines).")
        return 1
    backup = TARGET.with_suffix(".tsx.bak-detect")
    shutil.copy2(TARGET, backup)
    for _name, anchor, new in REPLACEMENTS:
        text = text.replace(anchor, new, 1)
    TARGET.write_text(text, encoding="utf-8")
    print(f"Patched OK: {TARGET} (backup: {backup})")
    print("Hard-refresh the browser (Ctrl+Shift+R) to load the Detect tab.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
