# OE-DELIVERY: 2026-10-29-doc-intel-v3-viewer-highlight-patch3
"""Patch live frontend/src/modules/pdf-takeoff/TakeoffViewerModule.tsx
(third highlight fix): panel highlights WITHOUT opening the Find
popup, plus the visibility fixes from patch_viewer_highlight2.py if
that one was not run yet - this script supersedes it and tolerates
either state.

Run once from the repo root (no backend restart; hard-refresh after):

    python patch_viewer_highlight3.py

Requires patch_viewer_highlight.py (the bridge) to be applied first.

Why: the bridge opened the viewer's Find popup on every panel click
because the text-layer scan only runs while the popup is open. A new
panelHighlightRef now lets the scan run - and the highlight boxes
draw - with the popup closed. (If the Find popup is already open it
stays open; Clear highlight in the panel turns the highlight off.)

Also included when missing (same as patch_viewer_highlight2.py):
    * active match drawn with a padded box + thick dark outline
    * panel-requested matches framed at a readable zoom (>= 1.75x)

Each edit is applied only when its exact old text is present and
skipped when its new text is already there; any other mismatch
aborts with nothing written. A .bak copy is written first.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

TARGET = Path("frontend/src/modules/pdf-takeoff/TakeoffViewerModule.tsx")

V1_MARKER = "handlePanelHighlight"

# (name, old, new) - old None means the edit is skipped when `new`
# is already present and required otherwise.
DRAW_OLD = """        const isActive = k === activeMatchIdx;
        ctx.globalAlpha = isActive ? 0.45 : 0.25;
        ctx.fillStyle = isActive ? '#F59E0B' : '#FACC15';
        ctx.fillRect(x, y, w, h);
        if (isActive) {
          ctx.globalAlpha = 0.95;
          ctx.lineWidth = 1.5 * dpr;
          ctx.strokeStyle = '#D97706';
          ctx.strokeRect(x, y, w, h);
        }"""
DRAW_NEW = """        const isActive = k === activeMatchIdx;
        ctx.globalAlpha = isActive ? 0.45 : 0.25;
        ctx.fillStyle = isActive ? '#F59E0B' : '#FACC15';
        ctx.fillRect(x, y, w, h);
        if (isActive) {
          // Padded box + thick dark outline: at full-page zoom a plain
          // 1.5px stroke over small sheet text is easy to miss.
          const pad = 3 * dpr;
          ctx.globalAlpha = 0.95;
          ctx.lineWidth = 3 * dpr;
          ctx.strokeStyle = '#EA580C';
          ctx.strokeRect(x - pad, y - pad, w + pad * 2, h + pad * 2);
        }"""

BRIDGE_OLD = """    const idx = searchMatches.findIndex((m) => m.page === panelMatchRequest.page);
    if (idx >= 0) goToMatch(idx);
    else goToPage(panelMatchRequest.page);
    setPanelMatchRequest(null);
  }, [panelMatchRequest, searchBusy, searchMatches, goToMatch, goToPage]);"""
BRIDGE_NEW = """    const idx = searchMatches.findIndex((m) => m.page === panelMatchRequest.page);
    if (idx >= 0) {
      goToMatch(idx);
      // goToMatch keeps the current zoom when the match run is wide,
      // which can leave the word tiny at full-page view. Frame the
      // match at a readable zoom too; the double frame delay lets
      // this centering land after goToMatch's own scroll frame.
      const match = searchMatches[idx]!;
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          const vp = viewportSize();
          if (vp.width === 0 || vp.height === 0) return;
          const targetZoom = Math.min(3, Math.max(zoomRef.current || 1, 1.75));
          setZoom(targetZoom);
          requestAnimationFrame(() => {
            const c = containerRef.current;
            if (!c) return;
            const midX = (match.box.minX + match.box.maxX) / 2;
            const midY = (match.box.minY + match.box.maxY) / 2;
            c.scrollLeft = Math.max(0, midX * targetZoom - vp.width / 2);
            c.scrollTop = Math.max(0, midY * targetZoom - vp.height / 2);
          });
        });
      });
    } else {
      goToPage(panelMatchRequest.page);
    }
    setPanelMatchRequest(null);
  }, [panelMatchRequest, searchBusy, searchMatches, goToMatch, goToPage, viewportSize]);"""

REF_OLD = """  const scannedQueryRef = useRef('');"""
REF_NEW = """  const scannedQueryRef = useRef('');
  // True while a panel-requested highlight is active: lets the find
  // scan run and the highlight boxes draw WITHOUT opening the Find
  // popup (the scan normally only runs while the popup is open).
  const panelHighlightRef = useRef(false);"""

GUARD_OLD = """    if (!pdfDoc || !searchOpen || q.length === 0) {"""
GUARD_NEW = """    if (!pdfDoc || (!searchOpen && !panelHighlightRef.current) || q.length === 0) {"""

HANDLER_OLD = """      setSearchOpen(true);
      setSearchQuery(q);
      setPanelMatchRequest({ term: q, page, nonce: Date.now() });"""
HANDLER_NEW = """      panelHighlightRef.current = true;
      setSearchQuery(q);
      setPanelMatchRequest({ term: q, page, nonce: Date.now() });"""

CLEAR_OLD = """  const clearPanelHighlight = useCallback(() => {
    setPanelMatchRequest(null);
    setSearchOpen(false);
    setSearchQuery('');
  }, []);"""
CLEAR_NEW = """  const clearPanelHighlight = useCallback(() => {
    setPanelMatchRequest(null);
    panelHighlightRef.current = false;
    setSearchOpen(false);
    setSearchQuery('');
  }, []);"""

EDITS = (
    ("active match outline", DRAW_OLD, DRAW_NEW),
    ("bridge framing", BRIDGE_OLD, BRIDGE_NEW),
    ("panel highlight ref", REF_OLD, REF_NEW),
    ("scan guard", GUARD_OLD, GUARD_NEW),
    ("handler no-popup", HANDLER_OLD, HANDLER_NEW),
    ("clear resets ref", CLEAR_OLD, CLEAR_NEW),
)


def main() -> int:
    if not TARGET.exists():
        print(f"TARGET MISSING: {TARGET} (run from the repo root)")
        return 1
    text = TARGET.read_text(encoding="utf-8")
    if V1_MARKER not in text:
        print("V1 MISSING: run patch_viewer_highlight.py first, nothing changed.")
        return 1
    staged = []
    for name, old, new in EDITS:
        if new in text:
            print(f"  skip (already present): {name}")
            continue
        if text.count(old) != 1:
            print(f"ANCHOR MISSING/AMBIGUOUS ({name}): found {text.count(old)}x, nothing changed.")
            return 1
        staged.append((name, old, new))
    if not staged:
        print("Already applied: all highlight fixes present, nothing changed.")
        return 0
    backup = TARGET.with_suffix(".tsx.bak4")
    shutil.copy2(TARGET, backup)
    for _name, old, new in staged:
        text = text.replace(old, new, 1)
    TARGET.write_text(text, encoding="utf-8")
    print(f"Patched OK: {TARGET} (backup: {backup})")
    print("Hard-refresh the browser (Ctrl+Shift+R) to load the changes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
