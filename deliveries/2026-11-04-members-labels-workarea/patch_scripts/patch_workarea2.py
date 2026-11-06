# OE-DELIVERY 2026-11-04-takeoff-workarea: no videos bar in compact PDF Measurements, shorter
# default Markups list, slimmer drawings strip -> the drawing gets the room.
from pathlib import Path
import sys

ROOT = Path(sys.argv[1])


def patch(rel, pairs):
    p = ROOT / rel
    s = p.read_text(encoding='utf-8')
    for old, new in pairs:
        if s.count(old) != 1:
            print('ANCHOR FAIL', rel, s.count(old), old[:140])
            sys.exit(1)
        s = s.replace(old, new)
    p.write_text(s, encoding='utf-8')


patch('features/videos/ModuleVideosSlot.tsx', [
    ("""export function ModuleVideosSlot() {
  const { pathname } = useLocation();
  const route = videoRouteFor(pathname);
  const hidden = useVideoHintsStore((s) => (route ? s.off || s.hidden.includes(route) : true));
  if (!route || hidden) return null;""", """/** PDF Measurements in compact mode hides this bar so the drawing gets the
 *  room (OE-DELIVERY 2026-11-04-takeoff-workarea). */
function useTakeoffCompact(pathname: string): boolean {
  const read = () => {
    try { return pathname.startsWith('/takeoff') && localStorage.getItem('takeoff.compactHeader') !== '0'; } catch { return false; }
  };
  const [on, setOn] = useState(read);
  useEffect(() => {
    setOn(read());
    const h = () => setOn(read());
    window.addEventListener('takeoff-compact-change', h);
    return () => window.removeEventListener('takeoff-compact-change', h);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname]);
  return on;
}

export function ModuleVideosSlot() {
  const { pathname } = useLocation();
  const route = videoRouteFor(pathname);
  const hidden = useVideoHintsStore((s) => (route ? s.off || s.hidden.includes(route) : true));
  const compactTakeoff = useTakeoffCompact(pathname);
  if (!route || hidden || compactTakeoff) return null;"""),
])

patch('features/takeoff/TakeoffPage.tsx', [
    ("""    try { localStorage.setItem('takeoff.compactHeader', compactHeader ? '1' : '0'); } catch { /* ignore */ }
  }, [compactHeader]);""", """    try { localStorage.setItem('takeoff.compactHeader', compactHeader ? '1' : '0'); } catch { /* ignore */ }
    window.dispatchEvent(new Event('takeoff-compact-change'));
  }, [compactHeader]);"""),
    # slimmer strip
    ("""    <div className="shrink-0 bg-surface-primary border border-border-light rounded-xl mt-3 overflow-hidden">
      {/* Header — always visible */}
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex items-center w-full px-4 py-2 cursor-pointer group hover:bg-surface-secondary/40 transition-colors"
      >""", """    <div className="shrink-0 bg-surface-primary border border-border-light rounded-xl mt-1.5 overflow-hidden">
      {/* Header — always visible */}
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex items-center w-full px-3 py-1 cursor-pointer group hover:bg-surface-secondary/40 transition-colors"
      >"""),
    ("""        <div className="flex items-center gap-2 px-4 pb-2.5 overflow-x-auto">""",
     """        <div className="flex items-center gap-2 px-3 pb-1.5 overflow-x-auto">"""),
])

patch('modules/pdf-takeoff/TakeoffViewerModule.tsx', [
    ("""const LEDGER_DEFAULT = 220;""", """// Shorter by default so the drawing gets the room; drag to enlarge
// (OE-DELIVERY 2026-11-04-takeoff-workarea).
const LEDGER_DEFAULT = 170;"""),
])
s = (ROOT / 'features/videos/ModuleVideosSlot.tsx').read_text(encoding='utf-8')
if 'useState' not in s.split('export function')[0]:
    s = "import { useEffect, useState } from 'react';\n" + s
    (ROOT / 'features/videos/ModuleVideosSlot.tsx').write_text(s, encoding='utf-8')
print('ok')
