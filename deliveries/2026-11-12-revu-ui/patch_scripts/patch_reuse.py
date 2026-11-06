"""Reuse toggle in the status bar next to SNAP: tools stay on after each
markup (sticky, remembered) (OE-DELIVERY 2026-11-12-revu-ui)."""
from pathlib import Path

p = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\frontend\src\modules\pdf-takeoff\TakeoffViewerModule.tsx")
s = p.read_text(encoding="utf-8")


def rep(a, b, n=1):
    global s
    c = s.count(a)
    assert c == n, (c, a[:100])
    s = s.replace(a, b)


rep("""  const [toolLock, setToolLock] = useState(false);
  const toolLockRef = useRef(false);
  toolLockRef.current = toolLock;""", """  const [toolLock, setToolLock] = useState(false);
  /** Status-bar REUSE: every tool stays on for the next markup until it is
   *  switched off (remembered between sessions). */
  const [reuseTools, setReuseTools] = useState<boolean>(() => {
    try { return localStorage.getItem('oe-reuse-tools') === '1'; } catch { return false; }
  });
  const toolLockRef = useRef(false);
  toolLockRef.current = toolLock || reuseTools;""")

rep("""              locked={toolLock}
              onLock""", """              locked={toolLock || reuseTools}
              onLock""")

rep("""                  SNAP
                </button>""", """                  SNAP
                </button>
                <button
                  type="button"
                  onClick={() => setReuseTools((x) => { const next = !x; try { localStorage.setItem('oe-reuse-tools', next ? '1' : '0'); } catch { /* ignore */ } return next; })}
                  aria-pressed={reuseTools}
                  title={reuseTools ? 'Reuse tools is ON: a tool stays on after each markup (Esc or Select to stop). Click to turn off.' : 'Reuse tools: keep the tool on after each markup so you can draw many in a row.'}
                  className={clsx(
                    'inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-bold tracking-wide border',
                    reuseTools ? 'border-oe-blue bg-oe-blue/10 text-oe-blue' : 'border-border text-content-tertiary',
                  )}
                  data-testid="revu-status-reuse"
                >
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <path d="M17 2l4 4-4 4" /><path d="M3 11V9a3 3 0 0 1 3-3h15" /><path d="M7 22l-4-4 4-4" /><path d="M21 13v2a3 3 0 0 1-3 3H3" />
                  </svg>
                  REUSE
                </button>""")
p.write_text(s, encoding="utf-8")
print("ok")
