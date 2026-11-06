# OE-DELIVERY 2026-11-03-structural-tool-chest: chest uses the AISC/SSMA-by-use library, header/jamb shapes
from pathlib import Path
import sys

ROOT = Path(sys.argv[1])


def patch(rel, pairs):
    p = ROOT / rel
    s = p.read_text(encoding='utf-8')
    for old, new in pairs:
        if s.count(old) != 1:
            print('ANCHOR FAIL', rel, s.count(old), old[:120])
            sys.exit(1)
        s = s.replace(old, new)
    p.write_text(s, encoding='utf-8')


patch('data/tool-chest-sets.ts', [
    ("export type ShapeFamily = 'W' | 'WT' | 'HSS' | 'HSSR' | 'L' | 'C' | 'CFS-S' | 'CFS-T' | 'DECK' | 'JOIST';",
     "export type ShapeFamily = 'W' | 'WT' | 'HSS' | 'HSSR' | 'L' | 'C' | 'CFS-S' | 'CFS-T' | 'DECK' | 'JOIST' | 'HDR' | 'JAMB';"),
    ("  JOIST: 'Joist / Truss',\n};", "  JOIST: 'Joist / Truss',\n  HDR: 'Header',\n  JAMB: 'Jamb',\n};"),
    ("""    const t = (raw ?? '').trim().toUpperCase().replace(/\\s+/g, '');
    if (!t) continue;""", """    const t = (raw ?? '').trim().toUpperCase().replace(/\\s+/g, '').replace(/^\\(?\\d\\)?-/, '');
    if (!t) continue;
    if (/JAMB/.test(t)) return 'JAMB';
    if (/HDR|HEADER|BOXBEAM/.test(t)) return 'HDR';"""),
    ("""    if (/^L\\d/.test(t)) return 'L';""", """    if (/^L\\d/.test(t) || /^\\d{3,4}L\\d/.test(t)) return 'L';"""),
    ("""const STRUCTURAL_FLAG = 'takeoff.toolChest.structural.v1';""", """const STRUCTURAL_FLAG = 'takeoff.toolChest.structural.v2';"""),
    ("""interface LibraryFolderLike {
  id: string;
  name: string;
  color: string;
  defaultTool: string;
  materials: { id: string; designation: string; description: string }[];
}""", """interface LibraryFolderLike {
  id: string;
  name: string;
  color: string;
  defaultTool: string;
  /** Member role written as the Subject (structural-tools.ts). */
  subject?: string;
  strokeWidth?: number;
  materials: { id: string; designation: string; description: string }[];
}"""),
    ("""  return library.map((folder) => ({
    id: `lib-${folder.id}`,""", """  return library.map((folder) => ({
    id: folder.id.startsWith('zs-') ? folder.id : `lib-${folder.id}`,"""),
    ("""      const subject = fam ? FAMILY_NAMES[fam] : folder.name;
      return {
        id: `lib-${mat.id}`,""", """      const subject = folder.subject ?? (fam ? FAMILY_NAMES[fam] : folder.name);
      return {
        id: `${folder.id.startsWith('zs-') ? 'zs' : 'lib'}-${mat.id}`,"""),
    ("""        group: `${folder.name}: ${mat.designation.toUpperCase()}`,
        style: cleanStyle({ color: folder.color, strokeWidth: folder.defaultTool === 'area' ? 1.5 : 3 }),""",
     """        group: `${subject}: ${mat.designation.toUpperCase()}`,
        style: cleanStyle({ color: folder.color, strokeWidth: folder.strokeWidth ?? (folder.defaultTool === 'area' ? 1.5 : 3) }),"""),
    ("""  const have = new Set(sets.map((s) => s.id));
  return [...sets, ...structuralSets(library).filter((s) => !have.has(s.id))];""",
     """  // The first (material-library) structural sets are replaced by the
  // AISC / SSMA-by-use sets.
  const kept = sets.filter((s) => !s.id.startsWith('lib-'));
  const have = new Set(kept.map((s) => s.id));
  return [...kept, ...structuralSets(library).filter((s) => !have.has(s.id))];"""),
])

patch('components/RevuToolChest.tsx', [
    ("""    case 'JOIST':""", """    case 'HDR':
      return (<g {...sw} strokeWidth={2.2}><path d="M6 7 H24 V23 H6 Z" /><path d="M15 7 V23" /></g>);
    case 'JAMB':
      return (<g {...sw} strokeWidth={2.2}><path d="M13 6 H7 V24 H13" /><path d="M17 6 H23 V24 H17" /></g>);
    case 'JOIST':"""),
    ("""'CFS-T': 'TRK', DECK: 'DECK', JOIST: 'JST' };""", """'CFS-T': 'TRK', DECK: 'DECK', JOIST: 'JST', HDR: 'HDR', JAMB: 'JMB' };"""),
])
print('ok')
