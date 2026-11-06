# OE-DELIVERY 2026-11-03-auto-takeoff-members: chest sets for every Auto Takeoff member type.
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


patch('data/structural-tools.ts', [
    ("""  Header: '#EA580C',
  Jamb: '#9333EA',""", """  Header: '#EA580C',
  Jamb: '#9333EA',
  'Shear Wall': '#BE123C',
  'Load Bearing Header': '#EA580C',
  'Non-Load Bearing Header': '#F59E0B',
  'Load Bearing Jamb': '#9333EA',
  'Non-Load Bearing Jamb': '#C084FC',
  'CFS Joist': '#2563EB',
  'Hat Channel': '#0D9488',
  'Steel Joist': '#4F46E5',
  Deck: '#65A30D',"""),
    # W columns stay; add SJI joists + deck after angles
    ("""  {
    id: 'zs-lb-walls', name: 'SSMA · Load Bearing Walls',""", """  {
    id: 'zs-sji', name: 'SJI · Steel Joists (K / LH / DLH)', subject: 'Steel Joist', color: '#4F46E5', defaultTool: 'distance', strokeWidth: 3,
    materials: m('sji', [
      ['10K1', 'K-series open web joist, 10" deep'], ['12K1', 'K-series joist, 12" deep'], ['14K1', 'K-series joist, 14" deep'],
      ['16K3', 'K-series joist, 16" deep'], ['18K3', 'K-series joist, 18" deep'], ['18K5', 'K-series joist, 18" deep'],
      ['20K3', 'K-series joist, 20" deep'], ['22K4', 'K-series joist, 22" deep'], ['24K4', 'K-series joist, 24" deep'],
      ['26K5', 'K-series joist, 26" deep'], ['28K7', 'K-series joist, 28" deep'], ['30K8', 'K-series joist, 30" deep'],
      ['18LH03', 'LH-series long span joist, 18" deep'], ['24LH06', 'LH-series joist, 24" deep'], ['28LH07', 'LH-series joist, 28" deep'],
      ['32LH09', 'LH-series joist, 32" deep'], ['36LH10', 'LH-series joist, 36" deep'], ['40LH11', 'LH-series joist, 40" deep'],
      ['44LH12', 'LH-series joist, 44" deep'], ['48LH13', 'LH-series joist, 48" deep'], ['52DLH13', 'DLH-series deep long span, 52" deep'],
      ['60DLH15', 'DLH-series joist, 60" deep'], ['68DLH16', 'DLH-series joist, 68" deep'], ['72DLH17', 'DLH-series joist, 72" deep'],
    ]),
  },
  {
    id: 'zs-deck', name: 'Metal Deck (B / Composite / Form)', subject: 'Deck', color: '#65A30D', defaultTool: 'area', strokeWidth: 1.5,
    materials: m('deck', [
      ['1.5" B-22 GA', 'Type B wide rib roof deck, 22 ga'], ['1.5" B-20 GA', 'Type B wide rib roof deck, 20 ga'],
      ['1.5" B-18 GA', 'Type B wide rib roof deck, 18 ga'], ['1.5" F-22 GA', 'Type F intermediate rib roof deck, 22 ga'],
      ['1.5" A-22 GA', 'Type A narrow rib roof deck, 22 ga'], ['3" N-20 GA', 'Type N deep rib roof deck, 20 ga'],
      ['1.5" VL-20 GA', 'Composite floor deck 1-1/2", 20 ga'], ['2" VLI-20 GA', 'Composite floor deck 2", 20 ga'],
      ['2" VLI-18 GA', 'Composite floor deck 2", 18 ga'], ['3" VLI-20 GA', 'Composite floor deck 3", 20 ga'],
      ['0.6" C-26 GA', 'Form deck 9/16", 26 ga'], ['1" C-24 GA', 'Form deck 1", 24 ga'], ['1.5" CELLULAR DECK', 'Cellular deck 1-1/2"'],
    ]),
  },
  {
    id: 'zs-lb-walls', name: 'SSMA · Load Bearing Walls',"""),
    # shear walls before NLB walls
    ("""  {
    id: 'zs-nlb-walls', name: 'SSMA · Non-Load Bearing Walls',""", """  {
    id: 'zs-shear-walls', name: 'SSMA · Shear Walls', subject: 'Shear Wall', color: '#BE123C', defaultTool: 'polyline', strokeWidth: 5,
    materials: m('sw', [
      ['362S162-68', '3-5/8" shear wall stud, 68 mil'], ['362S162-97', '3-5/8" shear wall stud, 97 mil'],
      ['600S162-54', '6" shear wall stud, 54 mil'], ['600S162-68', '6" shear wall stud, 68 mil'], ['600S162-97', '6" shear wall stud, 97 mil'],
      ['600S200-97', '6" shear wall stud, 2" flange, 97 mil'], ['800S162-68', '8" shear wall stud, 68 mil'], ['800S200-97', '8" shear wall stud, 97 mil'],
      ['STRAP X-BRACE 4" 68 MIL', 'Flat strap X-bracing, 4" x 68 mil'],
    ]),
  },
  {
    id: 'zs-nlb-walls', name: 'SSMA · Non-Load Bearing Walls',"""),
    ("""    id: 'zs-headers', name: 'SSMA · Headers', subject: 'Header',""", """    id: 'zs-lb-headers', name: 'SSMA · Load Bearing Headers', subject: 'Load Bearing Header',"""),
    ("""      ['2-600S162-54 BOX HDR', 'Box header, (2) 6" studs 54 mil'], ['2-800S162-54 BOX HDR', 'Box header, (2) 8" studs 54 mil'],""",
     """      ['2-600S162-54 BOX HDR', 'Box header, (2) 6" studs 54 mil'], ['2-800S162-54 BOX HDR', 'Box header, (2) 8" studs 54 mil'],"""),
    ("""    id: 'zs-jambs', name: 'SSMA · Jambs', subject: 'Jamb',""", """    id: 'zs-lb-jambs', name: 'SSMA · Load Bearing Jambs', subject: 'Load Bearing Jamb',"""),
    ("""  {
    id: 'zs-floor-joists', name: 'SSMA · Floor Joists', subject: 'Floor Joist',""", """  {
    id: 'zs-nlb-headers', name: 'SSMA · Non-Load Bearing Headers', subject: 'Non-Load Bearing Header', color: '#F59E0B', defaultTool: 'distance', strokeWidth: 3,
    materials: m('nhdr', [
      ['2-362S125-33 BOX HDR', 'Box header, (2) 3-5/8" studs 33 mil'], ['2-600S125-33 BOX HDR', 'Box header, (2) 6" studs 33 mil'],
      ['2-362S162-43 BOX HDR', 'Box header, (2) 3-5/8" studs 43 mil'], ['362T125-33 HDR TRACK', 'Header track 3-5/8", 33 mil'],
      ['600T125-33 HDR TRACK', 'Header track 6", 33 mil'], ['362L150-33 L-HDR', 'L-header angle 3-5/8" x 1-1/2", 33 mil'],
    ]),
  },
  {
    id: 'zs-nlb-jambs', name: 'SSMA · Non-Load Bearing Jambs', subject: 'Non-Load Bearing Jamb', color: '#C084FC', defaultTool: 'count', strokeWidth: 2,
    materials: m('njamb', [
      ['2-362S125-30 JAMB', 'Jamb, (2) 3-5/8" studs 30 mil'], ['2-362S125-33 JAMB', 'Jamb, (2) 3-5/8" studs 33 mil'],
      ['2-600S125-33 JAMB', 'Jamb, (2) 6" studs 33 mil'], ['2-362S162-43 JAMB', 'Jamb, (2) 3-5/8" studs 43 mil'],
    ]),
  },
  {
    id: 'zs-floor-joists', name: 'SSMA · CFS Joists', subject: 'CFS Joist',"""),
    ("""  {
    id: 'zs-track', name: 'SSMA · Track & Accessories',""", """  {
    id: 'zs-hat', name: 'SSMA · Hat Channels (Furring)', subject: 'Hat Channel', color: '#0D9488', defaultTool: 'distance', strokeWidth: 2,
    materials: m('hat', [
      ['087F125-18', '7/8" hat (furring) channel, 18 mil (25 ga)'], ['087F125-30', '7/8" hat channel, 30 mil (20 ga EQ)'],
      ['087F125-33', '7/8" hat channel, 33 mil (20 ga)'], ['150F125-18', '1-1/2" hat channel, 18 mil'],
      ['150F125-30', '1-1/2" hat channel, 30 mil'], ['150F125-33', '1-1/2" hat channel, 33 mil'],
      ['RC-1 RESILIENT CHANNEL', 'Resilient channel 1/2", 25 ga'],
    ]),
  },
  {
    id: 'zs-track', name: 'SSMA · Track & Accessories',"""),
])

patch('data/tool-chest-sets.ts', [
    ("""export type ShapeFamily = 'W' | 'WT' | 'HSS' | 'HSSR' | 'L' | 'C' | 'CFS-S' | 'CFS-T' | 'DECK' | 'JOIST' | 'HDR' | 'JAMB';""",
     """export type ShapeFamily = 'W' | 'WT' | 'HSS' | 'HSSR' | 'L' | 'C' | 'CFS-S' | 'CFS-T' | 'DECK' | 'JOIST' | 'HDR' | 'JAMB' | 'HAT';"""),
    ("""  HDR: 'Header',
  JAMB: 'Jamb',
};""", """  HDR: 'Header',
  JAMB: 'Jamb',
  HAT: 'Hat Channel',
};"""),
    ("""    if (/JAMB/.test(t)) return 'JAMB';""", """    if (/JAMB/.test(t)) return 'JAMB';
    if (/^\\d{3}F\\d{3}/.test(t) || /HAT|FURRING|RESILIENT/.test(t)) return 'HAT';
    if (/DECK/.test(t) || /^\\d(\\.\\d+)?"[A-Z]{1,3}-/.test(t)) return 'DECK';"""),
    ("""const STRUCTURAL_FLAG = 'takeoff.toolChest.structural.v2';""", """const STRUCTURAL_FLAG = 'takeoff.toolChest.structural.v3';"""),
    ("""  const kept = sets.filter((s) => !s.id.startsWith('lib-'));""", """  // A new library version replaces the library sets (zs-*); the button only
  // adds the ones that are missing.
  const kept = sets.filter((s) => !s.id.startsWith('lib-') && (force || !s.id.startsWith('zs-')));"""),
])

patch('components/RevuToolChest.tsx', [
    ("""    case 'JOIST':""", """    case 'HAT':
      return <path d="M3 21 H9 V9 H21 V21 H27" {...sw} strokeWidth={2.2} />;
    case 'JOIST':"""),
    ("""HDR: 'HDR', JAMB: 'JMB' };""", """HDR: 'HDR', JAMB: 'JMB', HAT: 'HAT' };"""),
])
print('ok')
