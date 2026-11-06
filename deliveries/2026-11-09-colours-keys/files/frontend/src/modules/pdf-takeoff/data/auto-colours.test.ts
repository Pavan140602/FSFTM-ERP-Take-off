import { describe, expect, it } from 'vitest';
import { AutoColours, colourKey, HEADER_COLOURS, WALL_COLOURS } from './auto-colours';
import type { AutoItem } from './auto-takeoff';

const wall = (over: Partial<AutoItem> = {}): AutoItem =>
  ({
    key: 'k',
    category: 'walls',
    kind: 'line',
    designation: 'W1',
    label: 'W1',
    role: 'Bearing wall',
    profile: '600S200-68',
    page: 1,
    segment: 'wall',
    stud_spacing_in: 24,
    wall_width_in: 6,
    ...over,
  }) as AutoItem;

describe('auto colours', () => {
  it('headers take warm picklist colours, walls cool ones', () => {
    const c = new AutoColours(null);
    expect(HEADER_COLOURS).toContain(c.colourFor(wall({ segment: 'header', designation: 'W1 HEADER' })));
    expect(WALL_COLOURS).toContain(c.colourFor(wall()));
  });

  it('same parameters -> same colour; any change -> another colour', () => {
    const c = new AutoColours(null);
    const base = c.colourFor(wall());
    expect(c.colourFor(wall({ key: 'other' }))).toBe(base);
    const seen = new Set([
      base,
      c.colourFor(wall({ profile: '362S162-33' })),
      c.colourFor(wall({ stud_spacing_in: 16 })),
      c.colourFor(wall({ wall_width_in: 8 })),
      c.colourFor(wall({ role: 'Shear wall' })),
    ]);
    expect(seen.size).toBe(5);
    expect(colourKey(wall())).not.toBe(colourKey(wall({ stud_spacing_in: 16 })));
  });

  it('keeps the colours of a drawing between runs', () => {
    localStorage.removeItem('t.ac');
    const a = new AutoColours('t.ac');
    a.colourFor(wall());
    const second = a.colourFor(wall({ profile: 'X' }));
    a.save();
    const b = new AutoColours('t.ac');
    expect(b.colourFor(wall({ profile: 'X' }))).toBe(second);
  });
});
