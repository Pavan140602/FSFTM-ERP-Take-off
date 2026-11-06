/**
 * Auto Takeoff colours from the Revu picklist, one per set of parameters
 * (OE-DELIVERY 2026-11-09-colours-keys).
 *
 * Every auto markup gets its colour from the Revu-style picklist palette:
 *   - header areas and header tags: a warm family (oranges, reds, browns);
 *   - walls: a cool family (blues, greens, purples ...);
 *   - every other member: the remaining picklist colours.
 * Markups that differ in any parameter - role, material / profile, stud
 * spacing, wall width, height, header or plain wall - get a different
 * colour; the same parameters always get the same colour on a drawing
 * (the assignment is kept per document, so re-runs keep the colours).
 */
import type { AutoItem } from './auto-takeoff';

/** Picklist colours by family, most distinct first. */
export const HEADER_COLOURS = ['#FF8000', '#C00000', '#E46C0A', '#804000', '#FF0000', '#800000', '#C4BD00', '#FFC080', '#FF9999', '#808000'];
export const WALL_COLOURS = ['#0070C0', '#00B050', '#7030A0', '#0098A6', '#C0007A', '#000080', '#008000', '#400080', '#008080', '#0000FF', '#8000FF', '#FF00FF', '#800080', '#99CCFF', '#CC99FF', '#99FF99'];
export const MEMBER_COLOURS = ['#0000FF', '#00B050', '#C0007A', '#0098A6', '#7030A0', '#E46C0A', '#008000', '#000080', '#C00000', '#8000FF', '#008080', '#804000', '#FF00FF', '#400080', '#C4BD00', '#0070C0'];

export type ColourFamily = 'header' | 'wall' | 'member';

function familyOf(item: AutoItem): ColourFamily {
  if (item.segment === 'header' || /header/i.test(item.role ?? '')) return 'header';
  if (item.category === 'walls') return 'wall';
  return 'member';
}

/** The parameters that decide a markup's colour. */
export function colourKey(item: AutoItem): string {
  const fam = familyOf(item);
  const material = (item.profile || item.designation || '').toUpperCase().replace(/\s+/g, '');
  const parts = [fam, item.category, item.role ?? '', material];
  if (item.category === 'walls') {
    parts.push(
      item.designation.toUpperCase(),
      String(item.stud_spacing_in ?? ''),
      item.wall_width_in ? String(Math.round(item.wall_width_in * 2) / 2) : '',
      item.height_ft ? String(Math.round(item.height_ft * 12)) : '',
    );
  }
  return parts.join('|');
}

const paletteFor = (fam: ColourFamily) => (fam === 'header' ? HEADER_COLOURS : fam === 'wall' ? WALL_COLOURS : MEMBER_COLOURS);

/** Colour assignment of one drawing: parameter key -> picklist colour. */
export class AutoColours {
  private map: Record<string, string>;
  constructor(private storageKey: string | null) {
    this.map = {};
    if (!storageKey) return;
    try {
      const raw = localStorage.getItem(storageKey);
      const v = raw ? JSON.parse(raw) : null;
      if (v && typeof v === 'object') this.map = v as Record<string, string>;
    } catch {
      /* ignore */
    }
  }

  /** The colour for an item: the one this parameter set already has on the
   *  drawing, else the next family colour not used yet (cycling once all
   *  are taken). */
  colourFor(item: AutoItem): string {
    const key = colourKey(item);
    const have = this.map[key];
    if (have) return have;
    const fam = key.split('|')[0] as ColourFamily;
    const palette = paletteFor(fam);
    const used = new Map<string, number>();
    for (const [k, c] of Object.entries(this.map)) if (k.startsWith(`${fam}|`)) used.set(c, (used.get(c) ?? 0) + 1);
    let best = palette[0]!;
    let bestUse = Infinity;
    for (const c of palette) {
      const u = used.get(c) ?? 0;
      if (u < bestUse) {
        best = c;
        bestUse = u;
      }
    }
    this.map[key] = best;
    return best;
  }

  save(): void {
    if (!this.storageKey) return;
    try {
      localStorage.setItem(this.storageKey, JSON.stringify(this.map));
    } catch {
      /* ignore */
    }
  }
}
