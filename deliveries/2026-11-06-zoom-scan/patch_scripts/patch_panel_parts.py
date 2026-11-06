from pathlib import Path
import os

os.chdir(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\frontend\src\modules\pdf-takeoff")
p = Path('AutoTakeoffPanel.tsx')
s = p.read_text(encoding='utf-8')


def rep(a, b):
    global s
    assert s.count(a) == 1, (s.count(a), a[:70])
    s = s.replace(a, b)


rep('''  /** House framing rules: per sheet kind, only what that sheet is for. */
  rules: boolean;
  /** Saved choices already include the framing-rules member types. */''', '''  /** House framing rules: per sheet kind, only what that sheet is for. */
  rules: boolean;
  /** Zoomed check: parts each sheet is split into (0 = by how busy it is)
   *  (OE-DELIVERY 2026-11-06-zoom-scan). */
  zoomParts?: number;
  /** Saved choices already include the framing-rules member types. */''')
rep('''          framing_rules: prefs.rules,
        },
        { longRunning: true },''', '''          framing_rules: prefs.rules,
          detail_scan: true,
          zoom_parts: prefs.zoomParts ?? 0,
        },
        { longRunning: true },''')
rep('''        <label className="flex items-start gap-1.5 cursor-pointer">
          <input type="checkbox" checked={prefs.useAi} onChange={(e) => setPrefs((p) => ({ ...p, useAi: e.target.checked }))} data-testid="auto-use-ai" />''', '''        <label className="flex items-center gap-1.5" title="Each sheet is split into parts and every part is checked zoomed in, one by one: columns, beams, joists and deck.">
          <span>
            <b>Zoom in by parts</b> <span className="text-content-tertiary">— split each sheet into</span>
          </span>
          <select
            className="rounded border border-border bg-surface px-1 py-0.5"
            value={prefs.zoomParts ?? 0}
            onChange={(e) => setPrefs((p) => ({ ...p, zoomParts: Number(e.target.value) }))}
            data-testid="auto-zoom-parts"
          >
            <option value={0}>Auto (by how busy)</option>
            <option value={4}>4 parts</option>
            <option value={6}>6 parts</option>
            <option value={9}>9 parts</option>
            <option value={12}>12 parts</option>
            <option value={16}>16 parts</option>
          </select>
        </label>
        <label className="flex items-start gap-1.5 cursor-pointer">
          <input type="checkbox" checked={prefs.useAi} onChange={(e) => setPrefs((p) => ({ ...p, useAi: e.target.checked }))} data-testid="auto-use-ai" />''')
rep('''  zoom_scan?: {
    tiles?: number;
    shapes_checked?: number;
    added?: number;
    removed?: number;
    beams?: { labels_checked?: number; labelled_added?: number; unlabelled_added?: number };
  } | null;''', '''  zoom_scan?: {
    tiles?: number;
    shapes_checked?: number;
    added?: number;
    removed?: number;
    beams?: { labels_checked?: number; labelled_added?: number; unlabelled_added?: number };
    joists?: { callouts_checked?: number; callouts_framed?: number; members_added?: number };
    deck?: { added?: number };
    deck_legend?: string[];
    parts?: number;
    grid?: [number, number];
    log?: { part: number; row: number; col: number; rect: [number, number, number, number]; counts: Record<string, number>; missed: number }[];
  } | null;''')
rep('''            const tiles = sum((z) => z.tiles);
            const cols = sum((z) => z.added);
            const removed = sum((z) => z.removed);
            const beams = sum((z) => z.beams?.labelled_added);
            const unlabelled = sum((z) => z.beams?.unlabelled_added);
            return (
              <p className="text-content-secondary" data-testid="auto-zoom-scan">
                <b>Detailed scan:</b> {tiles} areas checked zoomed in''', '''            const tiles = sum((z) => z.parts ?? z.tiles);
            const cols = sum((z) => z.added);
            const removed = sum((z) => z.removed);
            const beams = sum((z) => z.beams?.labelled_added);
            const unlabelled = sum((z) => z.beams?.unlabelled_added);
            const joists = sum((z) => z.joists?.members_added);
            const decks = sum((z) => z.deck?.added);
            const withLog = last.res.pages.filter((pg) => pg.zoom_scan?.log?.length);
            return (
              <div className="space-y-0.5" data-testid="auto-zoom-scan">
              <p className="text-content-secondary">
                <b>Zoomed check:</b> {tiles} part{tiles === 1 ? '' : 's'} checked one by one
                {joists ? ` · +${joists} joist/truss line${joists === 1 ? '' : 's'}` : ''}
                {decks ? ` · +${decks} deck bay${decks === 1 ? '' : 's'}` : ''}''')
rep('''                {!cols && !removed && !beams && !unlabelled ? ' · nothing more found' : ''}
              </p>
            );''', '''                {!cols && !removed && !beams && !unlabelled && !joists && !decks ? ' · nothing more found' : ''}
              </p>
              {withLog.length > 0 && (
                <details className="text-content-secondary" data-testid="auto-zoom-parts-log">
                  <summary className="cursor-pointer">Part by part</summary>
                  {withLog.map((pg) => (
                    <div key={pg.page} className="ms-2">
                      <p className="font-semibold">
                        p.{pg.page} — {pg.zoom_scan!.grid ? `${pg.zoom_scan!.grid[0]} × ${pg.zoom_scan!.grid[1]}` : ''} parts
                      </p>
                      {pg.zoom_scan!.log!.map((l) => (
                        <button
                          key={l.part}
                          type="button"
                          className="flex w-full items-center gap-1.5 rounded px-1 py-0.5 text-start hover:bg-surface-secondary"
                          title="Zoom to this part"
                          onClick={() =>
                            onFocusSpot ? onFocusSpot(pg.page, (l.rect[0] + l.rect[2]) / 2, (l.rect[1] + l.rect[3]) / 2) : onJumpToPage(pg.page)
                          }
                          data-testid="auto-zoom-part-row"
                        >
                          <span>Part {l.part}</span>
                          <span className="text-content-tertiary">
                            {Object.entries(l.counts).map(([k, v]) => `${v} ${k}`).join(' · ') || 'nothing to take off'}
                          </span>
                          {l.missed > 0 && <span className="ms-auto text-amber-700">{l.missed} to check</span>}
                        </button>
                      ))}
                    </div>
                  ))}
                </details>
              )}
              </div>
            );''')
p.write_text(s, encoding='utf-8')
print('ok')
