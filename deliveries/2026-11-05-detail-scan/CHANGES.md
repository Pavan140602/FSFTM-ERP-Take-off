# 2026-11-05 (part 4): Detailed scan, no silent misses

Apply after `2026-11-05-takeoff-accuracy`. Restore with `python deliveries/2026-11-05-detail-scan/restore.py`, then **restart the backend**. All house framing rules are unchanged.

## What changed

1. **Every tag is checked.** After the takeoff, every structural tag on each plan sheet must have a markup of its type within 4 ft (or at its leader's end).
   - Tags that don't appear in **"Not taken off (n)"** in the Auto Takeoff results.
   - Each row shows the tag, its type and the sheet; clicking it zooms to the tag on that sheet.
   - When nothing is missed, the panel says "Every tag on the plans read was taken off."
2. **Combined tags on framing plans:** "W4 J-3" and "W1 J-1" now frame the J-3 / J-1 joists. The wall type belongs to the wall plan, so it is skipped there.
3. **Legend boxes ignored:** sample tags inside a LEGEND box are no longer taken off. The legend's "T-1" sample had been framed as a truss bay: 42 false trusses on S201 and 10 on the roof.
4. **Bays sharing joist lines:** where a short end bay (RJ-1) continues a corridor (J-1) at the same spacing, each joist goes to the nearest tag. The RJ-1 end bay is no longer swallowed by the corridor.
5. **Last-chance read:** when a joist or truss tag's leader ends on a single line, the joists drawn across that line within the bay are taken (double-line wall faces excluded).

## Result on the StudioRes set (23 sheets)

| Sheet | Tags not taken off |
|---|---|
| S200 foundation | 0 (20 columns, 20 base plates) |
| S201 framing | 0 (RJ-1 end bay now 28 joists; legend trusses removed) |
| S202, S203 framing | 0 (now identical bay for bay, as repeated floors should be) |
| S204 roof | 0 (legend "floor trusses" removed) |
| S205 1st floor shear walls | 1: W3 at the steel bay, where the wall meets a steel beam line and no double-line wall can be traced. It is listed for review. |
| S206â€“S208 | 0 |

The whole set runs in about 61 s.

## Checks

- **Backend tests:** 28 pass (11 framing-rules tests, 3 new; 17 existing Auto Takeoff tests).
- **Typecheck:** no new errors; the same 112 older errors remain.
- **Frontend tests:** 665 pass; the 6 failures are older.
