# OE-DELIVERY 2026-11-03-chest-names: tools show only the designation, AISC style (WT4x9).
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


patch('data/tool-chest-sets.ts', [
    ("""  group?: string;
  style: ToolStyle;
}

export interface ChestSet {""", """  group?: string;
  /** Description of the member (e.g. "Structural tee cut from W8x18"). */
  desc?: string;
  style: ToolStyle;
}

/** Designation as AISC prints it: W12x26, WT4x9, HSS6x6x1/4, Pipe4Std.
 *  SSMA designations (600S162-54) and names stay as they are. */
export function displayDesignation(name: string): string {
  const t = name.trim();
  const pipe = t.match(/^PIPE\\s*(\\d+(?:\\.\\d+)?)\\s*(STD|XS|XXS)$/i);
  if (pipe) return `Pipe${pipe[1]}${pipe[2]!.charAt(0).toUpperCase()}${pipe[2]!.slice(1).toLowerCase()}`;
  if (/^(W|WT|HSS|C|MC|L|S|M|HP|MT|ST)\\d/i.test(t)) return t.replace(/(?<=[\\d/])X(?=\\d)/gi, 'x').replace(/^([a-z]+)/i, (m) => m.toUpperCase());
  return t;
}

export interface ChestSet {"""),
    ("""  if (typeof o.group === 'string' && o.group) item.group = o.group.slice(0, 120);
  return item;""", """  if (typeof o.group === 'string' && o.group) item.group = o.group.slice(0, 120);
  if (typeof o.desc === 'string' && o.desc) item.desc = o.desc.slice(0, 200);
  return item;"""),
    ("""        label: mat.designation.toUpperCase(),
        group: `${subject}: ${mat.designation.toUpperCase()}`,""", """        label: mat.designation.toUpperCase(),
        desc: mat.description || undefined,
        group: `${subject}: ${mat.designation.toUpperCase()}`,"""),
])

patch('components/RevuToolChest.tsx', [
    ("""  addSet,
  newId,""", """  addSet,
  displayDesignation,
  newId,"""),
    # no family badge on the tile
    ("""        <span className="absolute -bottom-1 -right-1 rounded border border-border bg-surface-primary px-0.5 text-[7px] font-bold leading-[10px] text-content-secondary">{SHORT[fam]}</span>
""", ""),
    # tile caption
    ("""                          <span className="line-clamp-2 w-full break-words text-[9px] leading-tight text-content-primary">{item.name}</span>""",
     """                          <span className="line-clamp-2 w-full break-words text-[9px] leading-tight text-content-primary">{displayDesignation(item.name)}</span>"""),
    # list name + description
    ("""                            <span className="block truncate text-[11px] font-semibold text-content-primary">{item.name}</span>""",
     """                            <span className="block truncate text-[11px] font-semibold text-content-primary">{displayDesignation(item.name)}</span>"""),
    ("""                            {[(() => { const f = shapeFamily(item.label, item.name, item.subject); return f ? FAMILY_NAMES[f] : typeLabel(item.tool); })(), item.subject, item.label].filter(Boolean).filter((v, i, arr) => arr.indexOf(v) === i).join(' · ')}""",
     """                            {item.desc || [item.subject, typeLabel(item.tool)].filter(Boolean).join(' · ')}"""),
    ("""                        title={[item.name, item.subject && `Subject: ${item.subject}`, item.label && `Label: ${item.label}`, typeLabel(item.tool)].filter(Boolean).join('\\n')}""",
     """                        title={[displayDesignation(item.name), item.desc, item.subject && `Subject: ${item.subject}`, typeLabel(item.tool)].filter(Boolean).join('\\n')}"""),
])
print('ok')
