// OE-DELIVERY: 2026-11-12-revu-ui (scale input)
/**
 * Read a length typed any way an estimator writes it, to inches:
 *   12        12.0      12.5          (in the default unit)
 *   12'       12 ft     12.5'
 *   12'-6"    12' 6"    12'6"   12'-6 1/2"   12 ft 6 in   12'-6.5"
 *   6"        6 in      1/8"    3/4 in   1 1/2"   1-1/2"
 *   300 mm    30 cm     3.5 m   10 yd
 * Returns null when it cannot be read.
 */

export type LengthUnit = 'in' | 'ft' | 'mm' | 'cm' | 'm' | 'yd';

const IN_PER: Record<LengthUnit, number> = { in: 1, ft: 12, yd: 36, mm: 1 / 25.4, cm: 1 / 2.54, m: 1 / 0.0254 };

/** "6", "6.5", "1/2", "6 1/2", "6-1/2" -> number. */
function num(text: string): number | null {
  const t = text.trim();
  if (!t) return null;
  let m = t.match(/^(\d+(?:\.\d+)?)$/) || t.match(/^(\.\d+)$/);
  if (m) return Number(m[1]);
  m = t.match(/^(\d+)\s*\/\s*(\d+)$/);
  if (m) return Number(m[2]) ? Number(m[1]) / Number(m[2]) : null;
  m = t.match(/^(\d+(?:\.\d+)?)[\s-]+(\d+)\s*\/\s*(\d+)$/);
  if (m) return Number(m[3]) ? Number(m[1]) + Number(m[2]) / Number(m[3]) : null;
  return null;
}

export function parseLengthInches(text: string, defaultUnit: LengthUnit): number | null {
  let t = (text || '').trim().toLowerCase();
  if (!t) return null;
  t = t
    .replace(/[’′‘`]/g, "'")
    .replace(/[”″“]/g, '"')
    .replace(/''/g, '"')
    .replace(/\b(feet|foot)\b/g, 'ft')
    .replace(/\b(inches|inch)\b/g, 'in')
    .replace(/\s+/g, ' ');
  // Metric / yards with a unit.
  let m = t.match(/^(\d*\.?\d+)\s*(mm|cm|m|yd)$/);
  if (m) return Number(m[1]) * IN_PER[m[2] as LengthUnit];
  // Feet (+ inches): 12'  12'-6"  12' 6 1/2"  12ft 6in  12'-6.5"
  m = t.match(/^(\d*\.?\d+)\s*(?:'|ft)\s*-?\s*(.*)$/);
  if (m) {
    const ft = Number(m[1]);
    const rest = m[2]!.replace(/\s*(?:"|in)\s*$/, '').trim();
    if (!rest) return ft * 12;
    const inch = num(rest);
    return inch === null ? null : ft * 12 + inch;
  }
  // Inches with a unit: 6"  6 in  1/8"  1 1/2"  1-1/2"
  m = t.match(/^(.+?)\s*(?:"|in)$/);
  if (m) {
    const inch = num(m[1]!);
    return inch === null ? null : inch;
  }
  // No unit: the default one.
  const v = num(t);
  return v === null ? null : v * IN_PER[defaultUnit];
}

/** 150 -> 12'-6" ; fractions to 1/16". */
export function formatFtIn(inches: number): string {
  const sign = inches < 0 ? '-' : '';
  let x = Math.abs(inches);
  let ft = Math.floor(x / 12 + 1e-9);
  let rem = Math.round((x - ft * 12) * 16) / 16;
  if (rem >= 12) {
    ft += 1;
    rem -= 12;
  }
  const whole = Math.floor(rem + 1e-9);
  const frac = Math.round((rem - whole) * 16);
  let fracTxt = '';
  if (frac) {
    let n = frac;
    let d = 16;
    while (n % 2 === 0) {
      n /= 2;
      d /= 2;
    }
    fracTxt = ` ${n}/${d}`;
  }
  return `${sign}${ft}'-${whole}${fracTxt}"`;
}
