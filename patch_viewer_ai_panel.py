# OE-DELIVERY: 2026-10-28-doc-intel-viewer-patch
"""Patch live frontend/src/modules/pdf-takeoff/TakeoffViewerModule.tsx:
add the AI Assistant tab to the PDF Measurements right panel.

Run once from the repo root (frontend dev server picks the change up;
do a hard refresh in the browser afterwards):

    python patch_viewer_ai_panel.py

Base file MUST be the 18,043-line export build
(marker 2026-10-27-export-proposal). Anchor-verified + idempotent:
every anchor is checked BEFORE anything is written; on any mismatch
the file is left untouched. A .bak copy is written next to the file
first. If the AI tab is already present the script reports
"already applied" and changes nothing.

Changes (4 small insertions, no existing logic touched):
  1. Import AiAssistantPanel (new sibling file, delivered alongside).
  2. sidebarTab gains the 'ai' value (was 'properties' | 'tools' |
     'colours'). The tab persists via the existing localStorage key.
  3. Toolbar "AI Assistant" button (Sparkles) next to the Panel toggle:
     opens the right panel on the AI tab.
  4. "AI Assistant" tab button in the right panel's segmented control
     + the panel content itself, rendered only when sidebarTab === 'ai'.
     The panel reuses the existing right-panel drag-resize/collapse
     shell, so no new resize machinery is introduced. Page jumps use
     the viewer's own goToPage, so search results and Ask citations
     land on the right page in the same viewer.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

TARGET = Path("frontend/src/modules/pdf-takeoff/TakeoffViewerModule.tsx")

OLD_MARKER = "// OE-DELIVERY: 2026-10-27-export-proposal (was 2026-10-23-text-outside-save)"
NEW_MARKER = "// OE-DELIVERY: 2026-10-28-doc-intel (was 2026-10-27-export-proposal)"

ANCHOR_IMPORT = "import { apiGet, apiPost, getAuthToken } from '../../shared/lib/api';"
AFTER_IMPORT = ANCHOR_IMPORT + "\nimport AiAssistantPanel from './AiAssistantPanel';"

ANCHOR_TAB_TYPE = "useState<'properties' | 'tools' | 'colours'>"
NEW_TAB_TYPE = "useState<'properties' | 'tools' | 'colours' | 'ai'>"

ANCHOR_FULLSCREEN = "{/* Fullscreen the whole measurement workspace (strips +"
AI_TOOLBAR_BUTTON = """                  {/* AI Assistant - open the right panel on the AI tab. */}
                  <button
                    onClick={() => { setShowSidebar(true); setSidebarTab('ai'); }}
                    className={tbBtn(showSidebar && sidebarTab === 'ai')}
                    title={t('takeoff_viewer.ai_assistant', { defaultValue: 'AI Assistant: search and ask about this document' })}
                    aria-label={t('takeoff_viewer.ai_assistant', { defaultValue: 'AI Assistant' })}
                    aria-pressed={showSidebar && sidebarTab === 'ai'}
                    data-testid="ai-assistant-toggle"
                  >
                    <Sparkles size={15} />
                    <span className="takeoff-toolbar-label">{t('takeoff_viewer.ai_assistant_short', { defaultValue: 'AI Assistant' })}</span>
                  </button>
"""

ANCHOR_COLOURS_END = """                {t('takeoff_viewer.tab_colours', { defaultValue: 'Colours' })}
              </button>
            </div>"""
NEW_COLOURS_END = """                {t('takeoff_viewer.tab_colours', { defaultValue: 'Colours' })}
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={sidebarTab === 'ai'}
                onClick={() => setSidebarTab('ai')}
                className={clsx(
                  'flex-1 px-2 py-1 rounded text-[11px] font-semibold transition-colors',
                  sidebarTab === 'ai'
                    ? 'bg-oe-blue text-white shadow-sm'
                    : 'text-content-secondary hover:bg-surface-secondary',
                )}
                data-testid="sidebar-tab-ai"
              >
                {t('takeoff_viewer.tab_ai', { defaultValue: 'AI Assistant' })}
              </button>
            </div>"""

ANCHOR_TOOL_CHEST = "{/* Tool Chest — Bluebeam-style saved custom tools. */}"
AI_PANEL_BLOCK = """            {/* AI Assistant — document search + Ask AI for the open drawing. */}
            {sidebarTab === 'ai' && (
              <AiAssistantPanel
                documentId={documentId}
                currentPage={currentPage}
                onJumpToPage={goToPage}
              />
            )}

"""


def main() -> int:
    if not TARGET.exists():
        print(f"TARGET MISSING: {TARGET} (run from the repo root)")
        return 1
    text = TARGET.read_text(encoding="utf-8")
    if "AiAssistantPanel" in text and "sidebar-tab-ai" in text:
        print("Already applied: AI Assistant tab present, nothing changed.")
        return 0
    missing = []
    for name, anchor in [
        ("top marker", OLD_MARKER),
        ("api import", ANCHOR_IMPORT),
        ("sidebarTab type", ANCHOR_TAB_TYPE),
        ("fullscreen comment", ANCHOR_FULLSCREEN),
        ("colours tab end", ANCHOR_COLOURS_END),
        ("tool chest comment", ANCHOR_TOOL_CHEST),
    ]:
        if anchor not in text:
            missing.append(name)
    if missing:
        print(f"ANCHOR(S) MISSING: {', '.join(missing)} — nothing changed.")
        print("This patch expects the 18,043-line export build as its base.")
        return 1
    backup = TARGET.with_suffix(".tsx.bak")
    shutil.copy2(TARGET, backup)
    text = text.replace(OLD_MARKER, NEW_MARKER, 1)
    text = text.replace(ANCHOR_IMPORT, AFTER_IMPORT, 1)
    text = text.replace(ANCHOR_TAB_TYPE, NEW_TAB_TYPE, 1)
    text = text.replace(ANCHOR_FULLSCREEN, AI_TOOLBAR_BUTTON + ANCHOR_FULLSCREEN, 1)
    text = text.replace(ANCHOR_COLOURS_END, NEW_COLOURS_END, 1)
    text = text.replace(ANCHOR_TOOL_CHEST, AI_PANEL_BLOCK + ANCHOR_TOOL_CHEST, 1)
    TARGET.write_text(text, encoding="utf-8")
    print(f"Patched OK: {TARGET} (backup: {backup})")
    print("Hard-refresh the browser (Ctrl+Shift+R) to load the new panel.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
