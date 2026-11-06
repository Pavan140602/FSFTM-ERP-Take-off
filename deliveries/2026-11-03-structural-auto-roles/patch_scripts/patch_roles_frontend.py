# OE-DELIVERY 2026-11-03-auto-takeoff-roles (frontend): roles -> Subject, profile -> Material,
# Tool Chest colours, column marks on the sheet, structural chest library.
from pathlib import Path
import sys

ROOT = Path(sys.argv[1])


def patch(rel, pairs):
    p = ROOT / rel
    s = p.read_text(encoding='utf-8')
    for old, new in pairs:
        if s.count(old) != 1:
            print('ANCHOR FAIL', rel, s.count(old), old[:160])
            sys.exit(1)
        s = s.replace(old, new)
    p.write_text(s, encoding='utf-8')


patch('data/auto-takeoff.ts', [
    ("""  /** The same text as a band along its reading direction (4 corners). */
  label_quad?: number[][] | null;
}""", """  /** The same text as a band along its reading direction (4 corners). */
  label_quad?: number[][] | null;
  /** What the member is (Load Bearing Wall, Header, Floor Truss, Beam ...),
   *  read from schedules, notes and the sheet title (OE-DELIVERY 2026-11-03-auto-takeoff-roles). */
  role?: string | null;
  /** Profile resolved from a schedule row (e.g. wall tag W1 -> 600S162-54). */
  profile?: string | null;
  /** Column mark (C1, C2 ...) and where it is printed. */
  mark?: string | null;
  mark_quad?: number[][] | null;
}"""),
    ("""    ...(Array.isArray(item.label_quad) && item.label_quad.length === 4
      ? { lq: item.label_quad.map((q) => [q[0]!, q[1]!] as [number, number]) }
      : {}),
  };
}""", """    ...(Array.isArray(item.label_quad) && item.label_quad.length === 4
      ? { lq: item.label_quad.map((q) => [q[0]!, q[1]!] as [number, number]) }
      : {}),
    ...(item.role ? { role: item.role } : {}),
    ...(item.mark ? { mk: item.mark } : {}),
    ...(Array.isArray(item.mark_quad) && item.mark_quad.length === 4
      ? { mq: item.mark_quad.map((q) => [q[0]!, q[1]!] as [number, number]) }
      : {}),
  };
}"""),
])

# AutoTag fields
p = ROOT / 'data/auto-takeoff.ts'
s = p.read_text(encoding='utf-8')
a = s.index('export interface AutoTag {')
b = s.index('\n}', a)
s = s[:b] + """
  /** Member role (OE-DELIVERY 2026-11-03-auto-takeoff-roles). */
  role?: string;
  /** Column mark text and its quad on the sheet. */
  mk?: string;
  mq?: [number, number][];""" + s[b:]
p.write_text(s, encoding='utf-8')

V = 'TakeoffViewerModule.tsx'
patch(V, [
    ("""  type ChestSet,
} from './data/tool-chest-sets';
""", """  type ChestSet,
} from './data/tool-chest-sets';
import { ROLE_COLORS, STRUCTURAL_TOOLSETS } from './data/structural-tools';
"""),
    ("""  const [chestSets, setChestSets] = useState<ChestSet[]>(() => withStructuralSets(loadChestSets(), getCustomizedLibrary()));""",
     """  const [chestSets, setChestSets] = useState<ChestSet[]>(() => withStructuralSets(loadChestSets(), STRUCTURAL_TOOLSETS));"""),
    ("""    if (chestSets.some((x) => x.id.startsWith('lib-'))) markStructuralSeeded();""",
     """    if (chestSets.some((x) => x.id.startsWith('zs-'))) markStructuralSeeded();"""),
    ("""onAddStructural={() => setChestSets((prev) => withStructuralSets(prev, chestLibrary, true))}""",
     """onAddStructural={() => setChestSets((prev) => withStructuralSets(prev, STRUCTURAL_TOOLSETS, true))}"""),
    # build: role / profile / colour
    ("""      const build = (item: AutoItem): Measurement => {
        const meta = autoCategoryMeta(item.category);""", """      /** Colour of the Tool Chest tool for this profile, else the role colour
       *  (OE-DELIVERY 2026-11-03-auto-takeoff-roles). */
      const norm = (v: string | null | undefined) => (v ?? '').toUpperCase().replace(/\\s+/g, '');
      const chestByLabel = new Map<string, string>();
      for (const set of chestSetsRef.current) {
        if (set.recent) continue;
        for (const it of set.items) if (it.label && it.style.color && !chestByLabel.has(norm(it.label))) chestByLabel.set(norm(it.label), it.style.color);
      }
      const colourFor = (item: AutoItem, fallback: string): string =>
        chestByLabel.get(norm(item.profile ?? item.designation)) ?? (item.role ? ROLE_COLORS[item.role] : undefined) ?? fallback;
      const subjectFor = (item: AutoItem) => item.role || autoSubject(item.category);
      const genericSubjects = new Set(['Beam', 'Column', 'Joist', 'Truss', 'CFS Wall', 'Framing Area', 'Member', '']);
      const build = (item: AutoItem): Measurement => {
        const meta = autoCategoryMeta(item.category);"""),
    ("""          group: autoGroupName(item.category, item.designation),
          color: meta.color,""", """          group: autoGroupName(item.category, item.designation),
          color: colourFor(item, meta.color),"""),
    ("""          customFields: { Subject: autoSubject(item.category), Material: item.designation },
          auto: tagForItem(item, pts),
        };
        return { ...base, ...valueFor(base, pts) };""", """          customFields: { Subject: subjectFor(item), Material: item.profile || item.designation },
          auto: tagForItem(item, pts),
        };
        return { ...base, ...valueFor(base, pts) };"""),
    ("""          customFields: { ...m.customFields, Subject: m.customFields?.Subject || autoSubject(item.category), Material: item.designation },
          auto: tagForItem(item, pts),""", """          customFields: {
            ...m.customFields,
            // A Subject the user typed is kept; the generic one becomes the role.
            Subject: genericSubjects.has(m.customFields?.Subject ?? '') ? subjectFor(item) : m.customFields!.Subject!,
            Material: m.auto?.ud ? (m.customFields?.Material ?? item.designation) : item.profile || item.designation,
          },
          auto: { ...tagForItem(item, pts), ...(m.auto?.ud ? { des: m.auto.des, ud: true } : {}) },"""),
    # column marks on the sheet, in the highlight pass
    ("""        if (isSel && m.type === 'count') {
          ctx.globalAlpha = 1;
          ctx.strokeStyle = '#2563EB';""", """        if (isSel && m.type === 'count') {
          ctx.globalAlpha = 1;
          ctx.strokeStyle = '#2563EB';"""),
    ("""            ctx.stroke();
          }
        }
      }
      ctx.restore();
    }

    if (activeTool === 'select') {""", """            ctx.stroke();
          }
        }
      }
      ctx.restore();
    }
    // Column marks (OE-DELIVERY 2026-11-03-auto-takeoff-roles): every auto
    // column keeps a mark on the sheet - a small column symbol at the column
    // and its mark (C1 ...) or size beside it - and the printed mark text
    // lights up like the profile text.
    {
      const k = dpr * zoom;
      ctx.save();
      ctx.setLineDash([]);
      for (const m of measurements) {
        if (m.auto?.cat !== 'columns' || m.page !== currentPage) continue;
        if (hiddenGroups.has(m.group) || hiddenMeasurements.has(m.id) || hiddenTypes.has(m.type)) continue;
        const colour = resolveMeasurementColor(m, groupColorMap);
        const mq = m.auto.mq;
        if (mq && mq.length === 4) {
          ctx.globalAlpha = 0.38;
          ctx.fillStyle = '#FFE600';
          ctx.beginPath();
          ctx.moveTo(mq[0]![0] * k, mq[0]![1] * k);
          for (let qi = 1; qi < 4; qi++) ctx.lineTo(mq[qi]![0] * k, mq[qi]![1] * k);
          ctx.closePath();
          ctx.fill();
        }
        const text = m.auto.mk || '';
        for (const pt of m.points) {
          const x = pt.x * k;
          const y = pt.y * k;
          const r = Math.max(5 * dpr, 4.5 * k);
          ctx.globalAlpha = 1;
          if (!autoShowColumns) {
            // Column symbol: a ring with a cross, in the column colour.
            ctx.strokeStyle = colour;
            ctx.lineWidth = Math.max(1.5 * dpr, 0.9 * k);
            ctx.beginPath();
            ctx.arc(x, y, r, 0, Math.PI * 2);
            ctx.moveTo(x - r * 0.7, y - r * 0.7);
            ctx.lineTo(x + r * 0.7, y + r * 0.7);
            ctx.moveTo(x + r * 0.7, y - r * 0.7);
            ctx.lineTo(x - r * 0.7, y + r * 0.7);
            ctx.stroke();
          }
          if (text) {
            const fs = Math.max(9 * dpr, 6 * k);
            ctx.font = `bold ${fs}px Arial, Helvetica, sans-serif`;
            const w = ctx.measureText(text).width;
            const bx = x + r + 2 * dpr;
            const by = y - r - fs - 2 * dpr;
            ctx.fillStyle = 'rgba(255,255,255,0.92)';
            ctx.strokeStyle = colour;
            ctx.lineWidth = 1.2 * dpr;
            ctx.beginPath();
            if (typeof ctx.roundRect === 'function') ctx.roundRect(bx, by, w + 6 * dpr, fs + 4 * dpr, 3 * dpr);
            else ctx.rect(bx, by, w + 6 * dpr, fs + 4 * dpr);
            ctx.fill();
            ctx.stroke();
            ctx.fillStyle = colour;
            ctx.textBaseline = 'top';
            ctx.fillText(text, bx + 3 * dpr, by + 2 * dpr);
            ctx.textBaseline = 'alphabetic';
          }
        }
      }
      ctx.restore();
    }

    if (activeTool === 'select') {"""),
])

# chestSetsRef for applyAutoTakeoff (it runs async, outside render)
patch(V, [
    ("""  const [activeChestItemId, setActiveChestItemId] = useState<string | null>(null);""",
     """  const [activeChestItemId, setActiveChestItemId] = useState<string | null>(null);
  const chestSetsRef = useRef(chestSets);
  chestSetsRef.current = chestSets;"""),
])
print('ok')
