# OE-DELIVERY 2026-11-03-revu-wrapup: menu panels open, labelled rail, no Active Group,
# scale as a ratio, one-row toolbar, structural Tool Chest, Material Library removed.
from pathlib import Path
import re
import sys

P = Path(sys.argv[1])
s = P.read_text(encoding='utf-8')


def rep(old, new, count=1):
    global s
    c = s.count(old)
    if c != count:
        print('ANCHOR FAIL (found %d want %d)\n%s' % (c, count, old[:260]))
        sys.exit(1)
    s = s.replace(old, new)


# imports
rep("""  recordRecent,
  saveSets as saveChestSets,""", """  recordRecent,
  saveSets as saveChestSets,
  withStructuralSets,""")
rep("""import {
  LayoutGrid as RvThumbsIcon,
  Bookmark as RvBookmarkIcon,
  Ruler as RvMeasureIcon,
  Briefcase as RvChestIcon,
  Scaling as RvScaleIcon,
  ListChecks as RvMarkupsIcon,
  Search as RvSearchIcon,
} from 'lucide-react';""", """import {
  GalleryVerticalEnd as RvThumbsIcon,
  BookMarked as RvBookmarkIcon,
  Ruler as RvMeasureIcon,
  Briefcase as RvChestIcon,
  Scaling as RvScaleIcon,
  BotMessageSquare as RvAiIcon,
  Search as RvSearchIcon,
} from 'lucide-react';""")

# 1. Menus open the panel (they only switched the tab, so a closed panel stayed closed)
rep("""                { label: 'Auto Takeoff…', onClick: () => { setShowSidebar(true); setSidebarTab('auto'); }, testId: 'revu-tools-auto' },""",
    """                { label: 'Auto Takeoff…', onClick: () => showRevuPanel('auto'), testId: 'revu-tools-auto' },""")
rep("""                { label: 'AI Assistant', onClick: () => { setShowSidebar(true); setSidebarTab('ai'); } },
                { label: 'Tool Chest', onClick: () => { setShowSidebar(true); setSidebarTab('tools'); } },""",
    """                { label: 'AI Assistant', onClick: () => showRevuPanel('ai') },
                { label: 'Tool Chest', shortcut: 'Alt+X', onClick: () => showRevuPanel('tools') },""")
rep("""                { label: 'Tool Chest', checked: showSidebar && sidebarTab === 'tools', onClick: () => { setShowSidebar(true); setSidebarTab('tools'); } },
                { label: 'AI Assistant', checked: showSidebar && sidebarTab === 'ai', onClick: () => { setShowSidebar(true); setSidebarTab('ai'); } },
                { label: 'Auto Takeoff', checked: showSidebar && sidebarTab === 'auto', onClick: () => { setShowSidebar(true); setSidebarTab('auto'); } },""",
    """                { label: 'Tool Chest', checked: sideVisible && sidebarTab === 'tools', onClick: () => showRevuPanel('tools') },
                { label: 'AI Assistant', checked: sideVisible && sidebarTab === 'ai', onClick: () => showRevuPanel('ai') },
                { label: 'Auto Takeoff', checked: sideVisible && sidebarTab === 'auto', onClick: () => showRevuPanel('auto') },""")
rep("""  /** Thumbnail whose sheet number is being typed (OE-DELIVERY 2026-11-02-revu-left-panel-v2). */""",
    """  /** Open a panel (never toggles it shut) - for menus and commands
   *  (OE-DELIVERY 2026-11-03-revu-wrapup). */
  const showRevuPanel = useCallback(
    (key: 'thumbs' | 'index' | 'measure' | 'scale' | 'tools' | 'ai' | 'auto') => {
      const isSide = key === 'tools' || key === 'ai' || key === 'auto';
      if (isSide) {
        sidebarTabFirstRef.current = false;
        sidebarTabPrevRef.current = key;
        setSidebarTab(key);
        setShowSidebar(true);
        if (panelSide === 'left') {
          setLeftTab('side');
          setShowThumbnails(true);
        }
      } else {
        setLeftTab(key);
        setShowThumbnails(true);
      }
    },
    [panelSide],
  );
  /** Thumbnail whose sheet number is being typed (OE-DELIVERY 2026-11-02-revu-left-panel-v2). */""")

# 2. Rail: Revu-like icons with a caption under each, no Markups List
rep("""            className="flex w-9 shrink-0 flex-col items-center gap-1 rounded-lg border border-border bg-surface-secondary/70 py-1.5"
            role="tablist\"""", """            className="flex w-[52px] shrink-0 flex-col items-center gap-1 rounded-lg border border-border bg-surface-secondary/70 py-1.5"
            role="tablist\"""")
rep("""              ['thumbs', 'Thumbnails (Alt+T)', RvThumbsIcon],
              ['index', 'Bookmarks / Page Index (Alt+B)', RvBookmarkIcon],
              ['measure', 'Measurements (Alt+U)', RvMeasureIcon],
              ['tools', 'Tool Chest (Alt+X)', RvChestIcon],
              ['scale', 'Scale & Calibration', RvScaleIcon],
              ['sep', '', null],
              ['ai', 'AI Assistant', Sparkles],
              ['auto', 'Auto Takeoff', WandSparkles],
              ['sep2', '', null],
              ['markups', 'Markups List (Alt+L)', RvMarkupsIcon],
              ['search', 'Search (Ctrl+F)', RvSearchIcon],""", """              ['thumbs', 'Thumbnails (Alt+T)', RvThumbsIcon],
              ['index', 'Bookmarks / Page Index (Alt+B)', RvBookmarkIcon],
              ['measure', 'Measurements (Alt+U)', RvMeasureIcon],
              ['tools', 'Tool Chest (Alt+X)', RvChestIcon],
              ['scale', 'Scale & Calibration', RvScaleIcon],
              ['sep', '', null],
              ['ai', 'AI Assistant', RvAiIcon],
              ['auto', 'Auto Takeoff', WandSparkles],
              ['sep2', '', null],
              ['search', 'Search (Ctrl+F)', RvSearchIcon],""")
rep("""              if (key === 'markups' || key === 'search') {
                const on = key === 'markups' ? showLedger : searchOpen;""", """              // Caption under each icon so every tab reads at a glance.
              const caption = ({ thumbs: 'Thumbs', index: 'Index', measure: 'Measure', tools: 'Tools', scale: 'Scale', ai: 'AI', auto: 'Auto', search: 'Search' } as Record<string, string>)[key] ?? '';
              if (key === 'search') {
                const on = searchOpen;""")
rep("""                    onClick={() => {
                      if (key === 'markups') setShowLedger((x) => !x);
                      else setSearchOpen((v) => { if (!v) requestAnimationFrame(() => searchInputRef.current?.focus()); return !v; });
                    }}
                    data-testid={`rail-${key}`}
                    className={clsx(
                      'flex h-8 w-8 items-center justify-center rounded transition-colors',
                      on ? 'bg-oe-blue/15 text-oe-blue' : 'text-content-secondary hover:bg-surface-tertiary hover:text-content-primary',
                    )}
                  >
                    <Icon size={16} />
                  </button>""", """                    onClick={() => setSearchOpen((v) => { if (!v) requestAnimationFrame(() => searchInputRef.current?.focus()); return !v; })}
                    data-testid={`rail-${key}`}
                    className={clsx(
                      'flex w-11 flex-col items-center justify-center gap-0.5 rounded py-1 transition-colors',
                      on ? 'bg-oe-blue/15 text-oe-blue' : 'text-content-secondary hover:bg-surface-tertiary hover:text-content-primary',
                    )}
                  >
                    <Icon size={17} />
                    <span className="text-[9px] font-medium leading-none">{caption}</span>
                  </button>""")
# the generic rail button
s, n = re.subn(
    r"""(                  data-testid=\{`rail-\$\{key\}`\}
                  className=\{clsx\(
                    )'flex h-8 w-8 items-center justify-center rounded transition-colors',
(                    active \? 'bg-oe-blue text-white shadow-sm' : 'text-content-secondary hover:bg-surface-tertiary hover:text-content-primary',
                  \)\}
                >
                  )<Icon size=\{16\} />""",
    lambda m: m.group(1) + "'flex w-11 flex-col items-center justify-center gap-0.5 rounded py-1 transition-colors',\n" + m.group(2) + "<Icon size={17} />\n                  <span className=\"text-[9px] font-medium leading-none\">{caption}</span>",
    s)
if n != 1:
    print('rail button regex', n)
    sys.exit(1)

# 3. Active Group block removed from the side panel
a = s.index("            {/* Active group selector */}")
b = s.index("            {/* Count label (when count tool active) */}", a)
s = s[:a] + "            {/* Active Group selector removed (OE-DELIVERY 2026-11-03-revu-wrapup): markups take their group from the tool. */}\n\n" + s[b:]

# 4. Scale reads as a drawing scale, not pixels
rep("""                {(() => {
                  // Stored scale is pixels-per-metre (D-TKC-016); show the
                  // per-pixel length in the user's measurement system.
                  const perPixel = convertQuantity(
                    1 / scale.pixelsPerUnit,
                    scale.unitLabel,
                    measurementSystem,
                  );
                  return `1px = ${formatFixedDigits(perPixel.value, 4)} ${perPixel.unit}`;
                })()}""", """                {/* Drawing scale as on the sheet, with its ratio (OE-DELIVERY 2026-11-03-revu-wrapup). */}
                <span data-testid="scale-current">{badgeMainLabel}</span>
                {badgeMainLabel !== formatScaleRatio(scale) && (
                  <span className="ml-2 text-xs font-normal text-content-tertiary">({formatScaleRatio(scale)})</span>
                )}""")

# 5. Toolbar: one row that wraps (no fixed second row)
a = s.index("""              {/* Row 2: scale and the drawing tools. Scale controls lead, then""")
head = s[:a]
close_idx = head.rstrip().rfind("</div>")
s = head[:close_idx] + "{/* Row 2 merged into one wrapping row (OE-DELIVERY 2026-11-03-revu-wrapup). */}\n" + s[a:]
rep("""              <div className="flex items-center gap-1 flex-wrap">
              {/* Stamp preset (OE-DELIVERY 2026-10-30-revu-markup-tools):""", """              {/* Stamp preset (OE-DELIVERY 2026-10-30-revu-markup-tools):""")
rep("""                className="ml-auto inline-flex h-7 items-center gap-1.5 rounded-md bg-gradient-to-r from-violet-500 to-indigo-500""",
    """                className="inline-flex h-7 items-center gap-1.5 rounded-md bg-gradient-to-r from-violet-500 to-indigo-500""")
rep("""              <div className="ml-auto flex items-center gap-1.5">
                {/* View toggles */}""", """              <div className="flex flex-wrap items-center gap-1.5">
                {/* View toggles */}""")

# 6. Tool Chest: structural sets, new tool, no Material Library
rep("""  const [chestSets, setChestSets] = useState<ChestSet[]>(() => loadChestSets());""",
    """  const [chestSets, setChestSets] = useState<ChestSet[]>(() => withStructuralSets(loadChestSets(), getCustomizedLibrary()));""")
rep("""                typeLabel={(tool) => TYPE_LABELS[tool] ?? tool}
              >""", """                typeLabel={(tool) => TYPE_LABELS[tool] ?? tool}
                toolTypes={stripTools.filter((x) => x.tool !== 'select').map((x) => ({ tool: x.tool, label: x.label }))}
                onAddStructural={() => setChestSets((prev) => withStructuralSets(prev, getCustomizedLibrary(), true))}
              >""")
a = s.index("""                {/* ── Material Library (SSMA / AISC / Vulcraft) ─────────────── */}""")
b = s.index("""              </RevuToolChest>""", a)
s = s[:a] + s[b:]

P.write_text(s, encoding='utf-8')
print('ok')
