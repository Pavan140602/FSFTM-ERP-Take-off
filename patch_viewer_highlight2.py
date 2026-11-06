# OE-DELIVERY: 2026-10-29-doc-intel-v3-viewer-highlight-patch2
"""Patch live frontend/src/modules/pdf-takeoff/TakeoffViewerModule.tsx
(second highlight fix): make a panel-driven highlight impossible to
miss on a dense sheet.

Run once from the repo root (no backend restart; hard-refresh after):

    python patch_viewer_highlight2.py

Requires patch_viewer_highlight.py to be applied first (it checks
for the bridge it extends).

What the first runtime test showed: the bridge worked - the find
opened with the term and matches were found - but at full-page zoom
the active orange box over small sheet text was too faint to spot,
and goToMatch keeps the current zoom when the matched text run is
wide, so the view never moved in on the word. This patch:
    * draws the active match with a padded box and a thick dark
      orange outline (the built-in find's active match gets the
      same, more visible treatment)
    * after a panel-requested goToMatch, frames the match at a
      readable zoom (at least 1.75x, capped at 3x) centered on the
      word, landing after goToMatch's own scroll frame

Anchor-verified + idempotent: every anchor is checked BEFORE anything
is written; on any mismatch the file is left untouched. A .bak copy
is written next to the file first.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

TARGET = Path("frontend/src/modules/pdf-takeoff/TakeoffViewerModule.tsx")

ALREADY_MARKER = "goToMatch keeps the current zoom when the match run is wide"
V1_MARKER = "handlePanelHighlight"

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

REPLACEMENTS = (
    ("active match outline", DRAW_OLD, DRAW_NEW),
    ("bridge framing", BRIDGE_OLD, BRIDGE_NEW),
)


def main() -> int:
    if not TARGET.exists():
        print(f"TARGET MISSING: {TARGET} (run from the repo root)")
        return 1
    text = TARGET.read_text(encoding="utf-8")
    if ALREADY_MARKER in text:
        print("Already applied: highlight framing fix present, nothing changed.")
        return 0
    if V1_MARKER not in text:
        print("V1 MISSING: run patch_viewer_highlight.py first, nothing changed.")
        return 1
    for name, old, _new in REPLACEMENTS:
        if text.count(old) != 1:
            print(f"ANCHOR MISSING/AMBIGUOUS ({name}): found {text.count(old)}x, nothing changed.")
            return 1
    backup = TARGET.with_suffix(".tsx.bak3")
    shutil.copy2(TARGET, backup)
    for _name, old, new in REPLACEMENTS:
        text = text.replace(old, new, 1)
    TARGET.write_text(text, encoding="utf-8")
    print(f"Patched OK: {TARGET} (backup: {backup})")
    print("Hard-refresh the browser (Ctrl+Shift+R) to load the framing fix.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
