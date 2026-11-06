from pathlib import Path

base = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\frontend\src\modules\pdf-takeoff")
s = ""


def rep(a, b, n=1):
    global s
    assert s.count(a) == n, (s.count(a), a[:100])
    s = s.replace(a, b)


p = base / "data" / "auto-takeoff.ts"
s = p.read_text(encoding="utf-8")
rep("""  ss?: number;
  seg?: 'wall' | 'header';
}""", """  ss?: number;
  seg?: 'wall' | 'header';
  /** The user picked this markup's colour: re-runs keep it
   *  (OE-DELIVERY 2026-11-09-colours-keys). */
  uc?: boolean;
}""")
p.write_text(s, encoding="utf-8")

p = base / "TakeoffViewerModule.tsx"
s = p.read_text(encoding="utf-8")
rep("import { drawStudWall, studCount } from './data/stud-wall';\n",
    "import { drawStudWall, studCount } from './data/stud-wall';\nimport { AutoColours } from './data/auto-colours';\n")
rep("""  const ledgerDocKey = documentId || fileName || 'local';""", """  const ledgerDocKey = documentId || fileName || 'local';
  /** Where this drawing's Auto Takeoff colours are kept (OE-DELIVERY 2026-11-09-colours-keys). */
  const autoColourKeyRef = useRef('');
  autoColourKeyRef.current = `takeoff.autoColours.v1.${ledgerDocKey}`;""")
rep("""      const colourFor = (item: AutoItem, fallback: string): string =>
        chestByLabel.get(norm(item.profile ?? item.designation)) ?? (item.role ? ROLE_COLORS[item.role] : undefined) ?? fallback;""", """      // Colours from the Revu picklist, a different one for every set of
      // parameters (header / wall / material / spacing / width / height),
      // kept per drawing (OE-DELIVERY 2026-11-09-colours-keys). The Tool
      // Chest / role colours stay as the fallback when no item is given.
      const autoColours = new AutoColours(autoColourKeyRef.current);
      const colourFor = (item: AutoItem, _fallback: string): string => autoColours.colourFor(item);
      void chestByLabel;
      void ROLE_COLORS;""")
rep("""          auto: { ...tagForItem(item, pts), ...(m.auto?.ud ? { des: m.auto.des, ud: true } : {}) },
        };
        return { ...next, ...valueFor(next, pts) };
      };""", """          auto: { ...tagForItem(item, pts), ...(m.auto?.ud ? { des: m.auto.des, ud: true } : {}), ...(m.auto?.uc ? { uc: true } : {}) },
          // A colour the user picked is kept; otherwise the colour of its parameters.
          ...(m.auto?.uc ? {} : { color: autoColours.colourFor(item) }),
        };
        return { ...next, ...valueFor(next, pts) };
      };""")
rep("""      const keptIds = new Set(result.next.map((m) => m.id));
      for (const m of before) if (!keptIds.has(m.id) && m.serverId) registerDeletion(m.serverId);""", """      autoColours.save();
      const keptIds = new Set(result.next.map((m) => m.id));
      for (const m of before) if (!keptIds.has(m.id) && m.serverId) registerDeletion(m.serverId);""")
rep("""    setMeasurements((prev) => prev.map((m) => (set.has(m.id) ? { ...m, color: colour } : m)));""",
    """    setMeasurements((prev) => prev.map((m) => (set.has(m.id) ? { ...m, color: colour, ...(m.auto ? { auto: { ...m.auto, uc: true } } : {}) } : m)));""")
p.write_text(s, encoding="utf-8")
print("ok")
