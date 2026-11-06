"""Area tool: Revu top properties bar + the area options (units, depth,
slope) docked as a horizontal bar under it, not a floating popup. Shown
while the Area / Volume tool is on or an area is selected; gone once the
area is done (OE-DELIVERY 2026-11-12-revu-ui update 8)."""
from pathlib import Path

p = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\frontend\src\modules\pdf-takeoff\TakeoffViewerModule.tsx")
s = p.read_text(encoding="utf-8")


def rep(a, b, n=1):
    global s
    c = s.count(a)
    assert c == n, (c, a[:100])
    s = s.replace(a, b)


# 1. Cut the floating popup block.
start = s.index("      {showAreaPopup && areaPopupPos && (\n")
end = s.index("\n      )}\n", start) + len("\n      )}\n")
blk = s[start:end]
s = s[:start] + s[end:]

# 2. Make it a horizontal docked bar.
def brep(a, b):
    global blk
    assert a in blk, a[:80]
    blk = blk.replace(a, b)

brep("      {showAreaPopup && areaPopupPos && (\n", "            {showAreaPopup && (\n")
brep("""          className="fixed z-40 w-72 rounded-lg border border-border bg-[#1e1e1e] shadow-2xl"
          style={{ left: areaPopupPos.left, top: areaPopupPos.top }}
          data-testid="area-tool-popup\"""",
     """          className="mb-1.5 rounded-lg border border-border bg-[#1e1e1e] shadow-sm"
          data-testid="area-tool-popup\"""")
brep('<div className="space-y-2 p-3">', '<div className="flex flex-wrap items-center gap-x-4 gap-y-1 px-3 py-1.5">')
brep('<div className="flex items-center justify-between pb-1 border-b border-white/10">', '<div className="order-last ml-auto flex items-center gap-2">')
blk = blk.replace('<span className="text-[11px] font-semibold text-white/90">Area</span>', '')
blk = blk.replace('<span className="w-16 shrink-0 text-xs text-neutral-300">', '<span className="shrink-0 text-xs text-neutral-300">')
blk = blk.replace('className="w-full rounded border border-neutral-600', 'className="w-auto rounded border border-neutral-600')
blk = blk.replace('<div className="flex items-center gap-2">', '<div className="flex items-center gap-1.5">')
# re-indent by 6 spaces
blk = "\n".join(("      " + l if l.strip() else l) for l in blk.split("\n"))
blk = "            {/* Area options, docked at the top like Revu (update 8). */}\n" + blk.lstrip()
if not blk.endswith("\n"):
    blk += "\n"

# 3. Props bar for the armed Area / Volume tool too, then the area bar.
rep("""            ) : propsBar.mode === 'selection' && (
            <div className="mb-1.5">
              <RevuPropertiesBar""", """            ) : (propsBar.mode === 'selection' || (propsBar.mode === 'tool' && (activeTool === 'area' || activeTool === 'volume'))) && (
            <div className="mb-1.5">
              <RevuPropertiesBar""")
anchor = """                onLayoutFraming={() => setShowFraming(true)}
              />
            </div>
            )}
"""
assert s.count(anchor) == 1
s = s.replace(anchor, anchor + blk)

# 4. Hidden once the area is done: the area just finished is not "selected" for it.
rep("""  const showAreaPopup = !areaPopupDismissed && (activeTool === 'area' || (() => {""",
    """  const showAreaPopup = !areaPopupDismissed && (activeTool === 'area' || activeTool === 'volume' || (() => {""")
p.write_text(s, encoding="utf-8")
print("ok")
