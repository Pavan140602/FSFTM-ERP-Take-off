from pathlib import Path

p = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\frontend\src\modules\pdf-takeoff\TakeoffViewerModule.tsx")
s = p.read_text(encoding="utf-8")


def rep(a, b, n=1):
    global s
    assert s.count(a) == n, (s.count(a), a[:100])
    s = s.replace(a, b)


# drag state: companions
rep("""    /** The measurement the clone was copied from (abort reselect). */
    sourceId?: string;
  } | null>(null);""", """    /** The measurement the clone was copied from (abort reselect). */
    sourceId?: string;
    /** Other selected markups dragged along with this one (a body drag on
     *  any markup of a multi-selection moves them all)
     *  (OE-DELIVERY 2026-11-09-colours-keys). */
    companions?: { id: string; original: Measurement }[];
  } | null>(null);""")

# arm: companions on a body drag inside a multi-selection
rep("""          // body / interior -> translate the whole shape.
          activeVertexRef.current = null;
          dragRef.current = {
            mode: 'shape',
            measurementId: m.id,
            original: { ...m, points: [...m.points] },
            origPoints: [...m.points],
            vertexIndex: -1,
            startPt: pt,
            moved: false,
            lastPoints: [...m.points],
          };""", """          // body / interior -> translate the whole shape. When the markup is
          // part of a multi-selection, every selected markup on this sheet
          // moves with it.
          activeVertexRef.current = null;
          const multi = selectedLedgerIdsRef.current;
          const companions =
            multi.size > 1 && multi.has(m.id)
              ? onPage
                  .filter((x) => x.id !== m.id && multi.has(x.id) && !x.locked && !x.flattened)
                  .map((x) => ({ id: x.id, original: { ...x, points: [...x.points] } }))
              : undefined;
          dragRef.current = {
            mode: 'shape',
            measurementId: m.id,
            original: { ...m, points: [...m.points] },
            origPoints: [...m.points],
            vertexIndex: -1,
            startPt: pt,
            moved: false,
            lastPoints: [...m.points],
            companions,
          };""")

# move: companions follow
rep("""        const tip = ortho ? orthoSnap(drag.startPt, cur) : cur;
        next = translatePoints(drag.origPoints, tip.x - drag.startPt.x, tip.y - drag.startPt.y);
      }""", """        const tip = ortho ? orthoSnap(drag.startPt, cur) : cur;
        next = translatePoints(drag.origPoints, tip.x - drag.startPt.x, tip.y - drag.startPt.y);
        if (drag.companions && drag.companions.length > 0) {
          const dx = tip.x - drag.startPt.x;
          const dy = tip.y - drag.startPt.y;
          const byId = new Map(drag.companions.map((c) => [c.id, c.original]));
          setMeasurements((prev) =>
            prev.map((x) => {
              const o = byId.get(x.id);
              return o ? { ...x, points: translatePoints(o.points, dx, dy) } : x;
            }),
          );
        }
      }""")

# finish: commit / restore companions
rep("""        } else {
          // The committed geometry is the last dragged points (state only
          // holds the pre-drag copy mid-drag), recomputed server-side on PATCH.
          commitGeometryEdit(drag.measurementId, drag.original, drag.lastPoints);
        }""", """        } else {
          // The committed geometry is the last dragged points (state only
          // holds the pre-drag copy mid-drag), recomputed server-side on PATCH.
          commitGeometryEdit(drag.measurementId, drag.original, drag.lastPoints);
          // Markups dragged along: commit each at its moved position.
          if (drag.companions && drag.companions.length > 0) {
            const dx = drag.lastPoints[0]!.x - drag.origPoints[0]!.x;
            const dy = drag.lastPoints[0]!.y - drag.origPoints[0]!.y;
            for (const c of drag.companions) {
              commitGeometryEdit(c.id, c.original, translatePoints(c.original.points, dx, dy));
            }
          }
        }""")
rep("""        // Abort: restore the pre-drag geometry, no undo frame.
        setMeasurements((prev) =>
          prev.map((m) =>
            m.id === drag.measurementId
              ? { ...drag.original, points: [...drag.original.points] }
              : m,
          ),
        );""", """        // Abort: restore the pre-drag geometry, no undo frame.
        const back = new Map((drag.companions ?? []).map((c) => [c.id, c.original]));
        setMeasurements((prev) =>
          prev.map((m) => {
            if (m.id === drag.measurementId) return { ...drag.original, points: [...drag.original.points] };
            const o = back.get(m.id);
            return o ? { ...o, points: [...o.points] } : m;
          }),
        );""")

# keys: Page Up / Page Down change the page
rep("""      // Arrow keys nudge the selected markup(s) on the current
      // page: 1 unit per press, Shift for a bigger step; a burst of""", """      // Page Up / Page Down: previous / next page, always
      // (OE-DELIVERY 2026-11-09-colours-keys).
      if ((e.key === 'PageUp' || e.key === 'PageDown') && !e.ctrlKey && !e.metaKey && !e.altKey && shouldHandleShortcut(e.target)) {
        e.preventDefault();
        flipPageRef.current(e.key === 'PageDown' ? 1 : -1);
        return;
      }

      // Arrow keys nudge the selected markup(s) on the current
      // page: 1 unit per press, Shift for a bigger step; a burst of""")
p.write_text(s, encoding="utf-8")
print("ok")
