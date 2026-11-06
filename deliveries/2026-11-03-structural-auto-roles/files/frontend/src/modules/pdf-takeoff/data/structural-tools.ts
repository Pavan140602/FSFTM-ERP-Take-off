// OE-DELIVERY: 2026-11-03-structural-tool-chest
/**
 * Structural Tool Chest, profile by profile, in the spirit of the ZenTek Revu
 * structural tool sets (nothing copied from ZenTek; their chests are a paid
 * product): the most commonly used AISC shapes, and SSMA cold-formed steel
 * sorted by use (load bearing walls, non-load bearing walls, headers, jambs,
 * floor joists, floor trusses, roof trusses, track and accessories).
 *
 * Each set's `subject` is the member role Auto Takeoff writes on its markups
 * (see backend auto_takeoff.assign_roles), so an auto markup and a markup
 * drawn from the chest carry the same Subject, colour and profile.
 */

export interface StructuralSet {
  id: string;
  name: string;
  /** Member role = the markup Subject (matches Auto Takeoff roles). */
  subject: string;
  color: string;
  /** Takeoff tool the members are drawn with. */
  defaultTool: 'distance' | 'polyline' | 'count' | 'area';
  strokeWidth: number;
  materials: { id: string; designation: string; description: string }[];
}

/** Colour per role, shared by the chest and Auto Takeoff. */
export const ROLE_COLORS: Record<string, string> = {
  Beam: '#1D4ED8',
  Column: '#7C3AED',
  WT: '#4338CA',
  HSS: '#0F766E',
  'HSS Round / Pipe': '#0E7490',
  Channel: '#B45309',
  Angle: '#6B7280',
  'Load Bearing Wall': '#DC2626',
  'Non-Load Bearing Wall': '#16A34A',
  'CFS Wall': '#E11D48',
  Header: '#EA580C',
  Jamb: '#9333EA',
  'Floor Joist': '#2563EB',
  'Ceiling Joist': '#0284C7',
  'Roof Joist': '#1E3A8A',
  'Floor Truss': '#0891B2',
  'Roof Truss': '#92400E',
  Track: '#64748B',
  Stud: '#475569',
  'Framing Area': '#65A30D',
};

const m = (prefix: string, list: [string, string][]) =>
  list.map(([designation, description]) => ({
    id: `${prefix}-${designation.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`,
    designation,
    description,
  }));

const wBeam = (d: string) => [d, `Wide flange beam ${d.replace('W', 'W ').replace('X', ' x ')} lb/ft`] as [string, string];
const wCol = (d: string) => [d, `Wide flange column ${d.replace('W', 'W ').replace('X', ' x ')} lb/ft`] as [string, string];

export const STRUCTURAL_TOOLSETS: StructuralSet[] = [
  {
    id: 'zs-w-beams', name: 'AISC · W Beams', subject: 'Beam', color: ROLE_COLORS.Beam!, defaultTool: 'distance', strokeWidth: 3,
    materials: m('w', [
      'W8X10', 'W8X13', 'W8X18', 'W8X24', 'W10X12', 'W10X15', 'W10X19', 'W10X22', 'W10X26', 'W10X30',
      'W12X14', 'W12X16', 'W12X19', 'W12X22', 'W12X26', 'W12X30', 'W12X35', 'W14X22', 'W14X26', 'W14X30',
      'W14X34', 'W14X38', 'W16X26', 'W16X31', 'W16X36', 'W16X40', 'W16X50', 'W18X35', 'W18X40', 'W18X50',
      'W18X60', 'W21X44', 'W21X50', 'W21X62', 'W24X55', 'W24X62', 'W24X68', 'W24X76', 'W24X84', 'W27X84',
      'W30X90', 'W30X99', 'W33X118', 'W36X135', 'W40X211', 'W40X277',
    ].map(wBeam)),
  },
  {
    id: 'zs-w-columns', name: 'AISC · W Columns', subject: 'Column', color: ROLE_COLORS.Column!, defaultTool: 'count', strokeWidth: 2,
    materials: m('wc', [
      'W8X31', 'W8X35', 'W8X40', 'W8X48', 'W8X58', 'W8X67', 'W10X33', 'W10X39', 'W10X45', 'W10X49',
      'W10X54', 'W10X60', 'W10X68', 'W10X77', 'W12X40', 'W12X45', 'W12X53', 'W12X58', 'W12X65', 'W12X72',
      'W12X79', 'W12X87', 'W14X48', 'W14X53', 'W14X61', 'W14X68', 'W14X74', 'W14X82', 'W14X90', 'W14X99',
      'W14X109', 'W14X120',
    ].map(wCol)),
  },
  {
    id: 'zs-wt', name: 'AISC · WT', subject: 'WT', color: ROLE_COLORS.WT!, defaultTool: 'distance', strokeWidth: 3,
    materials: m('wt', [
      ['WT4X9', 'Structural tee cut from W8x18'], ['WT5X11', 'Structural tee cut from W10x22'], ['WT6X13', 'Structural tee cut from W12x26'],
      ['WT6X20', 'Structural tee cut from W12x40'], ['WT7X15', 'Structural tee cut from W14x30'], ['WT7X21.5', 'Structural tee cut from W14x43'],
      ['WT8X18', 'Structural tee cut from W16x36'], ['WT8X25', 'Structural tee cut from W16x50'], ['WT9X25', 'Structural tee cut from W18x50'],
      ['WT9X30', 'Structural tee cut from W18x60'], ['WT12X38', 'Structural tee cut from W24x76'],
    ]),
  },
  {
    id: 'zs-hss-rect', name: 'AISC · HSS Square & Rectangular', subject: 'HSS', color: ROLE_COLORS.HSS!, defaultTool: 'distance', strokeWidth: 3,
    materials: m('hss', [
      ['HSS3X3X1/4', 'Square tube 3x3, 1/4 wall'], ['HSS4X4X1/4', 'Square tube 4x4, 1/4 wall'], ['HSS4X4X3/8', 'Square tube 4x4, 3/8 wall'],
      ['HSS5X5X1/4', 'Square tube 5x5, 1/4 wall'], ['HSS5X5X3/8', 'Square tube 5x5, 3/8 wall'], ['HSS6X6X1/4', 'Square tube 6x6, 1/4 wall'],
      ['HSS6X6X3/8', 'Square tube 6x6, 3/8 wall'], ['HSS6X6X1/2', 'Square tube 6x6, 1/2 wall'], ['HSS8X8X3/8', 'Square tube 8x8, 3/8 wall'],
      ['HSS8X8X1/2', 'Square tube 8x8, 1/2 wall'], ['HSS10X10X1/2', 'Square tube 10x10, 1/2 wall'], ['HSS12X12X1/2', 'Square tube 12x12, 1/2 wall'],
      ['HSS16X16X5/8', 'Square tube 16x16, 5/8 wall'], ['HSS6X4X1/4', 'Rect tube 6x4, 1/4 wall'], ['HSS8X4X1/4', 'Rect tube 8x4, 1/4 wall'],
      ['HSS8X6X3/8', 'Rect tube 8x6, 3/8 wall'], ['HSS8X6X1/2', 'Rect tube 8x6, 1/2 wall'], ['HSS10X6X3/8', 'Rect tube 10x6, 3/8 wall'],
      ['HSS12X6X3/8', 'Rect tube 12x6, 3/8 wall'], ['HSS12X8X1/2', 'Rect tube 12x8, 1/2 wall'],
    ]),
  },
  {
    id: 'zs-hss-round', name: 'AISC · HSS Round & Pipe', subject: 'HSS Round / Pipe', color: ROLE_COLORS['HSS Round / Pipe']!, defaultTool: 'distance', strokeWidth: 3,
    materials: m('pipe', [
      ['HSS4.000X0.250', 'Round HSS 4" dia, 0.250 wall'], ['HSS4.500X0.237', 'Round HSS 4-1/2" dia'], ['HSS5.563X0.258', 'Round HSS 5-9/16" dia'],
      ['HSS6.625X0.280', 'Round HSS 6-5/8" dia'], ['HSS8.625X0.322', 'Round HSS 8-5/8" dia'], ['PIPE3STD', 'Standard pipe 3"'],
      ['PIPE4STD', 'Standard pipe 4"'], ['PIPE5STD', 'Standard pipe 5"'], ['PIPE6STD', 'Standard pipe 6"'], ['PIPE8STD', 'Standard pipe 8"'],
    ]),
  },
  {
    id: 'zs-channels', name: 'AISC · Channels (C / MC)', subject: 'Channel', color: ROLE_COLORS.Channel!, defaultTool: 'distance', strokeWidth: 3,
    materials: m('c', [
      ['C6X8.2', 'American standard channel 6"'], ['C8X11.5', 'American standard channel 8"'], ['C10X15.3', 'American standard channel 10"'],
      ['C12X20.7', 'American standard channel 12"'], ['C15X33.9', 'American standard channel 15"'], ['MC8X8.5', 'Miscellaneous channel 8"'],
      ['MC10X22', 'Miscellaneous channel 10"'], ['MC12X31', 'Miscellaneous channel 12"'],
    ]),
  },
  {
    id: 'zs-angles', name: 'AISC · Angles', subject: 'Angle', color: ROLE_COLORS.Angle!, defaultTool: 'distance', strokeWidth: 2,
    materials: m('l', [
      ['L2X2X1/4', 'Equal leg angle 2x2'], ['L3X3X1/4', 'Equal leg angle 3x3'], ['L3-1/2X3-1/2X1/4', 'Equal leg angle 3-1/2'],
      ['L4X4X1/4', 'Equal leg angle 4x4, 1/4'], ['L4X4X3/8', 'Equal leg angle 4x4, 3/8'], ['L5X5X3/8', 'Equal leg angle 5x5'],
      ['L6X6X3/8', 'Equal leg angle 6x6'], ['L4X3X1/4', 'Unequal leg angle 4x3'], ['L5X3X1/4', 'Unequal leg angle 5x3'],
      ['L6X4X3/8', 'Unequal leg angle 6x4'],
    ]),
  },
  {
    id: 'zs-lb-walls', name: 'SSMA · Load Bearing Walls', subject: 'Load Bearing Wall', color: ROLE_COLORS['Load Bearing Wall']!, defaultTool: 'polyline', strokeWidth: 4,
    materials: m('lbw', [
      ['362S162-43', '3-5/8" stud, 1-5/8" flange, 43 mil (18 ga)'], ['362S162-54', '3-5/8" stud, 1-5/8" flange, 54 mil (16 ga)'],
      ['362S162-68', '3-5/8" stud, 1-5/8" flange, 68 mil (14 ga)'], ['400S162-43', '4" stud, 43 mil (18 ga)'], ['400S162-54', '4" stud, 54 mil (16 ga)'],
      ['550S162-43', '5-1/2" stud, 43 mil (18 ga)'], ['550S162-54', '5-1/2" stud, 54 mil (16 ga)'], ['600S162-43', '6" stud, 43 mil (18 ga)'],
      ['600S162-54', '6" stud, 54 mil (16 ga)'], ['600S162-68', '6" stud, 68 mil (14 ga)'], ['600S162-97', '6" stud, 97 mil (12 ga)'],
      ['600S200-54', '6" stud, 2" flange, 54 mil'], ['600S200-68', '6" stud, 2" flange, 68 mil'], ['800S162-54', '8" stud, 54 mil (16 ga)'],
      ['800S162-68', '8" stud, 68 mil (14 ga)'], ['800S200-68', '8" stud, 2" flange, 68 mil'], ['800S200-97', '8" stud, 2" flange, 97 mil'],
    ]),
  },
  {
    id: 'zs-nlb-walls', name: 'SSMA · Non-Load Bearing Walls', subject: 'Non-Load Bearing Wall', color: ROLE_COLORS['Non-Load Bearing Wall']!, defaultTool: 'polyline', strokeWidth: 3,
    materials: m('nlbw', [
      ['250S125-18', '2-1/2" partition stud, 18 mil (25 ga)'], ['250S125-30', '2-1/2" partition stud, 30 mil (20 ga EQ)'],
      ['362S125-18', '3-5/8" partition stud, 18 mil (25 ga)'], ['362S125-30', '3-5/8" partition stud, 30 mil (20 ga EQ)'],
      ['362S125-33', '3-5/8" stud, 33 mil (20 ga)'], ['400S125-30', '4" partition stud, 30 mil'], ['600S125-18', '6" partition stud, 18 mil (25 ga)'],
      ['600S125-30', '6" partition stud, 30 mil (20 ga EQ)'], ['600S125-33', '6" stud, 33 mil (20 ga)'], ['600S162-33', '6" stud, 1-5/8" flange, 33 mil'],
      ['800S125-33', '8" stud, 33 mil (20 ga)'],
    ]),
  },
  {
    id: 'zs-headers', name: 'SSMA · Headers', subject: 'Header', color: ROLE_COLORS.Header!, defaultTool: 'distance', strokeWidth: 4,
    materials: m('hdr', [
      ['2-600S162-54 BOX HDR', 'Box header, (2) 6" studs 54 mil'], ['2-800S162-54 BOX HDR', 'Box header, (2) 8" studs 54 mil'],
      ['2-800S200-68 BOX HDR', 'Box header, (2) 8" studs 68 mil'], ['2-1000S200-68 BOX HDR', 'Box header, (2) 10" studs 68 mil'],
      ['2-1200S200-97 BOX HDR', 'Box header, (2) 12" studs 97 mil'], ['2-600S162-54 B2B HDR', 'Back-to-back header, (2) 6" studs'],
      ['2-800S162-68 B2B HDR', 'Back-to-back header, (2) 8" studs'], ['600L150-54 L-HDR', 'L-header angle 6" x 1-1/2", 54 mil'],
      ['800L150-68 L-HDR', 'L-header angle 8" x 1-1/2", 68 mil'], ['2-600T125-54 HDR TRACK', 'Header track, (2) 6" track 54 mil'],
    ]),
  },
  {
    id: 'zs-jambs', name: 'SSMA · Jambs', subject: 'Jamb', color: ROLE_COLORS.Jamb!, defaultTool: 'count', strokeWidth: 2,
    materials: m('jamb', [
      ['2-362S162-43 JAMB', 'Jamb, (2) 3-5/8" studs 43 mil'], ['2-362S162-54 JAMB', 'Jamb, (2) 3-5/8" studs 54 mil'],
      ['2-600S162-54 JAMB', 'Jamb, (2) 6" studs 54 mil'], ['3-600S162-54 JAMB', 'Jamb, (3) 6" studs 54 mil'],
      ['2-600S162-68 JAMB', 'Jamb, (2) 6" studs 68 mil'], ['2-600S200-68 JAMB', 'Jamb, (2) 6" studs 2" flange 68 mil'],
      ['2-800S162-54 JAMB', 'Jamb, (2) 8" studs 54 mil'], ['2-800S200-68 JAMB', 'Jamb, (2) 8" studs 2" flange 68 mil'],
    ]),
  },
  {
    id: 'zs-floor-joists', name: 'SSMA · Floor Joists', subject: 'Floor Joist', color: ROLE_COLORS['Floor Joist']!, defaultTool: 'distance', strokeWidth: 3,
    materials: m('fj', [
      ['800S200-54', '8" joist, 2" flange, 54 mil'], ['800S200-68', '8" joist, 2" flange, 68 mil'], ['1000S200-54', '10" joist, 54 mil'],
      ['1000S200-68', '10" joist, 68 mil'], ['1000S250-97', '10" joist, 2-1/2" flange, 97 mil'], ['1200S200-68', '12" joist, 68 mil'],
      ['1200S200-97', '12" joist, 97 mil'], ['1200S250-97', '12" joist, 2-1/2" flange, 97 mil'], ['1000T200-54 RIM', 'Rim track 10", 54 mil'],
      ['1200T200-68 RIM', 'Rim track 12", 68 mil'],
    ]),
  },
  {
    id: 'zs-floor-trusses', name: 'CFS · Floor Trusses', subject: 'Floor Truss', color: ROLE_COLORS['Floor Truss']!, defaultTool: 'distance', strokeWidth: 3,
    materials: m('ft', [
      ['FLOOR TRUSS 12"', 'Open-web floor truss, 12" deep'], ['FLOOR TRUSS 16"', 'Open-web floor truss, 16" deep'],
      ['FLOOR TRUSS 18"', 'Open-web floor truss, 18" deep'], ['FLOOR TRUSS 24"', 'Open-web floor truss, 24" deep'],
      ['FLOOR GIRDER TRUSS', 'Floor girder truss'], ['FLOOR TRUSS TCB', 'Floor truss, top chord bearing'],
    ]),
  },
  {
    id: 'zs-roof-trusses', name: 'CFS · Roof Trusses', subject: 'Roof Truss', color: ROLE_COLORS['Roof Truss']!, defaultTool: 'distance', strokeWidth: 3,
    materials: m('rt', [
      ['COMMON TRUSS', 'Common (gable) roof truss'], ['GIRDER TRUSS', 'Roof girder truss'], ['HIP TRUSS', 'Hip truss'],
      ['HIP GIRDER TRUSS', 'Hip girder truss'], ['JACK TRUSS', 'Jack truss'], ['MONO TRUSS', 'Mono-pitch truss'],
      ['SCISSOR TRUSS', 'Scissor truss'], ['GABLE END TRUSS', 'Gable end truss'], ['VALLEY TRUSS', 'Valley truss'],
      ['ATTIC TRUSS', 'Attic truss'],
    ]),
  },
  {
    id: 'zs-track', name: 'SSMA · Track & Accessories', subject: 'Track', color: ROLE_COLORS.Track!, defaultTool: 'distance', strokeWidth: 2,
    materials: m('trk', [
      ['362T125-33', '3-5/8" track, 33 mil'], ['362T125-43', '3-5/8" track, 43 mil'], ['600T125-43', '6" track, 43 mil'],
      ['600T125-54', '6" track, 54 mil'], ['800T125-54', '8" track, 54 mil'], ['1000T125-68', '10" track, 68 mil'],
      ['150U50-54 BRIDGING', 'U-channel bridging 1-1/2", 54 mil'], ['600S162-43 BLOCKING', 'Stud blocking 6", 43 mil'],
      ['STRAP 3" 54 MIL', 'Flat strap bracing 3", 54 mil'], ['CLIP ANGLE', 'Clip angle connection'],
    ]),
  },
];
