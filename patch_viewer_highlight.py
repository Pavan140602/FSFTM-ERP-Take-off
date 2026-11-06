# OE-DELIVERY: 2026-10-29-doc-intel-v3-viewer-highlight-patch
"""Patch live frontend/src/modules/pdf-takeoff/TakeoffViewerModule.tsx:
bridge the AI Assistant panel to the viewer's built-in find so a
panel result/citation click highlights the term ON the drawing.

Run once from the repo root (no backend restart; hard-refresh after):

    python patch_viewer_highlight.py

Requires the 2026-10-28 AI panel patch (patch_viewer_ai_panel.py) to
be applied first - it checks for the panel import and render block.

How it works: the viewer already has a complete find system (pdf.js
text-layer scan -> searchMatches -> canvas highlight boxes + the
goToMatch zoom-to-box framing). This patch only adds:
    * scannedQueryRef - remembers which term the latest scan was for
    * handlePanelHighlight(term, page) - opens find with the term and
      parks the request; an effect resolves it once that term's scan
      lands: goToMatch(first match on the page), else a plain page
      jump (scanned sheets have no text layer -> page-level only)
    * clearPanelHighlight() - closes find, which clears the matches
    * the two new props on the <AiAssistantPanel> element

Anchor-verified + idempotent: every anchor is checked BEFORE anything
is written; on any mismatch the file is left untouched. A .bak copy
is written next to the file first.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

TARGET = Path("frontend/src/modules/pdf-takeoff/TakeoffViewerModule.tsx")

ALREADY_MARKER = "handlePanelHighlight"
V1_MARKER = "import AiAssistantPanel from './AiAssistantPanel';"

REF_OLD = """  const textLayerCacheRef = useRef<Map<number, TextItem[]>>(new Map());"""
REF_NEW = """  const textLayerCacheRef = useRef<Map<number, TextItem[]>>(new Map());
  // Term the latest find scan actually computed matches for. The AI
  // panel highlight bridge compares against this so it never resolves
  // a request from a previous term's stale matches.
  const scannedQueryRef = useRef('');"""

SCAN_OLD = """        if (cancelled) return;
        setSearchMatches(all);"""
SCAN_NEW = """        if (cancelled) return;
        scannedQueryRef.current = q;
        setSearchMatches(all);"""

BRIDGE_ANCHOR = """  const prevPage = useCallback(() => {"""
BRIDGE_BLOCK = """  /* ── AI Assistant panel highlight bridge ──────────────────────────
   * The panel asks the viewer to highlight a term on a page; reuse the
   * built-in find machinery (text-layer scan + canvas highlights +
   * goToMatch framing) instead of a second highlight system. The scan
   * is async, so the request is parked and resolved by the effect
   * below once the scan for that exact term lands; if the term is not
   * on the requested page (or nowhere - scanned sheets have no text
   * layer), fall back to a plain page jump. */
  const [panelMatchRequest, setPanelMatchRequest] = useState<{
    term: string;
    page: number;
    nonce: number;
  } | null>(null);

  const handlePanelHighlight = useCallback(
    (term: string, page: number) => {
      const q = (term || '').trim();
      if (!q) {
        goToPage(page);
        return;
      }
      setSearchOpen(true);
      setSearchQuery(q);
      setPanelMatchRequest({ term: q, page, nonce: Date.now() });
    },
    [goToPage],
  );

  useEffect(() => {
    if (!panelMatchRequest || searchBusy) return;
    if (scannedQueryRef.current !== panelMatchRequest.term) return;
    const idx = searchMatches.findIndex((m) => m.page === panelMatchRequest.page);
    if (idx >= 0) goToMatch(idx);
    else goToPage(panelMatchRequest.page);
    setPanelMatchRequest(null);
  }, [panelMatchRequest, searchBusy, searchMatches, goToMatch, goToPage]);

  const clearPanelHighlight = useCallback(() => {
    setPanelMatchRequest(null);
    setSearchOpen(false);
    setSearchQuery('');
  }, []);

"""

PANEL_OLD = """              <AiAssistantPanel
                documentId={documentId}
                currentPage={currentPage}
                onJumpToPage={goToPage}
              />"""
PANEL_NEW = """              <AiAssistantPanel
                documentId={documentId}
                currentPage={currentPage}
                onJumpToPage={goToPage}
                onHighlightTerm={handlePanelHighlight}
                onClearHighlight={clearPanelHighlight}
              />"""

REPLACEMENTS = (
    ("scanned-query ref", REF_OLD, REF_NEW),
    ("scan term stamp", SCAN_OLD, SCAN_NEW),
    ("panel props", PANEL_OLD, PANEL_NEW),
)


def main() -> int:
    if not TARGET.exists():
        print(f"TARGET MISSING: {TARGET} (run from the repo root)")
        return 1
    text = TARGET.read_text(encoding="utf-8")
    if ALREADY_MARKER in text:
        print("Already applied: panel highlight bridge present, nothing changed.")
        return 0
    if V1_MARKER not in text:
        print("V1 MISSING: run patch_viewer_ai_panel.py first, nothing changed.")
        return 1
    for name, old, _new in REPLACEMENTS:
        if text.count(old) != 1:
            print(f"ANCHOR MISSING/AMBIGUOUS ({name}): found {text.count(old)}x, nothing changed.")
            return 1
    if text.count(BRIDGE_ANCHOR) != 1:
        print(f"ANCHOR MISSING/AMBIGUOUS (bridge): found {text.count(BRIDGE_ANCHOR)}x, nothing changed.")
        return 1
    backup = TARGET.with_suffix(".tsx.bak2")
    shutil.copy2(TARGET, backup)
    for _name, old, new in REPLACEMENTS:
        text = text.replace(old, new, 1)
    text = text.replace(BRIDGE_ANCHOR, BRIDGE_BLOCK + BRIDGE_ANCHOR, 1)
    TARGET.write_text(text, encoding="utf-8")
    print(f"Patched OK: {TARGET} (backup: {backup})")
    print("Hard-refresh the browser (Ctrl+Shift+R) to load the highlight bridge.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
