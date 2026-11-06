// DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
/**
 * Markups List power features (Bluebeam-style):
 *  - Formula columns: `=Value*2`, `=Area+Perimeter`, etc.
 *  - Filtering: by type, group, page, text.
 *  - Totals: sum values grouped by type.
 */

export interface MeasurementLike {
  id: string;
  type: string;
  value: number;
  unit: string;
  label: string;
  annotation: string;
  page: number;
  group: string;
  customFields?: Record<string, string>;
  depth?: number;
  area?: number;
}

/* ── Formula engine ─────────────────────────────────────────────── */

/** Fields available in formulas. */
const FIELD_GETTERS: Record<string, (m: MeasurementLike) => number | string> = {
  value: (m) => m.value,
  area: (m) => m.area ?? m.value,
  length: (m) => m.value,
  perimeter: (m) => m.value,
  depth: (m) => m.depth ?? 0,
  page: (m) => m.page,
  count: (m) => m.value,
};

function getField(m: MeasurementLike, name: string): number {
  const key = name.toLowerCase();
  if (FIELD_GETTERS[key]) {
    const v = FIELD_GETTERS[key]!(m);
    return typeof v === 'number' ? v : parseFloat(String(v)) || 0;
  }
  // Custom field
  const cf = m.customFields?.[name] ?? m.customFields?.[Object.keys(m.customFields || {}).find((k) => k.toLowerCase() === key) || ''];
  return parseFloat(String(cf || '0')) || 0;
}

/**
 * Evaluate a formula like `=Value*2+10` against a measurement.
 * Supports +, -, *, /, parentheses, and field names. Returns null on error.
 */
export function evaluateFormula(formula: string, m: MeasurementLike): number | null {
  let expr = formula.trim();
  if (expr.startsWith('=')) expr = expr.slice(1);
  if (!expr) return null;

  // Tokenize: numbers, identifiers, operators, parens
  const tokens: string[] = [];
  let i = 0;
  while (i < expr.length) {
    const c = expr[i]!;
    if (/\s/.test(c)) { i++; continue; }
    if (/[0-9.]/.test(c)) {
      let num = '';
      while (i < expr.length && /[0-9.]/.test(expr[i]!)) num += expr[i++]!;
      tokens.push(num);
    } else if (/[a-zA-Z_]/.test(c)) {
      let id = '';
      while (i < expr.length && /[a-zA-Z0-9_]/.test(expr[i]!)) id += expr[i++]!;
      tokens.push(id);
    } else if ('+-*/()'.includes(c)) {
      tokens.push(c);
      i++;
    } else {
      return null; // Invalid character
    }
  }

  // Shunting-yard to RPN
  const output: string[] = [];
  const ops: string[] = [];
  const prec: Record<string, number> = { '+': 1, '-': 1, '*': 2, '/': 2 };
  for (const t of tokens) {
    if (/^[0-9.]+$/.test(t) || /^[a-zA-Z_]/.test(t)) {
      output.push(t);
    } else if (t === '(') {
      ops.push(t);
    } else if (t === ')') {
      while (ops.length && ops[ops.length - 1] !== '(') output.push(ops.pop()!);
      if (!ops.length) return null;
      ops.pop();
    } else {
      while (ops.length && ops[ops.length - 1] !== '(' && (prec[ops[ops.length - 1]!] || 0) >= (prec[t] || 0)) {
        output.push(ops.pop()!);
      }
      ops.push(t);
    }
  }
  while (ops.length) {
    const o = ops.pop()!;
    if (o === '(') return null;
    output.push(o);
  }

  // Evaluate RPN
  const stack: number[] = [];
  for (const t of output) {
    if (/^[0-9.]+$/.test(t)) {
      stack.push(parseFloat(t));
    } else if (/^[a-zA-Z_]/.test(t)) {
      stack.push(getField(m, t));
    } else {
      if (stack.length < 2) return null;
      const b = stack.pop()!;
      const a = stack.pop()!;
      switch (t) {
        case '+': stack.push(a + b); break;
        case '-': stack.push(a - b); break;
        case '*': stack.push(a * b); break;
        case '/': stack.push(b !== 0 ? a / b : 0); break;
        default: return null;
      }
    }
  }
  return stack.length === 1 ? stack[0]! : null;
}

/* ── Filtering ────────────────────────────────────────────────── */

export interface MarkupFilter {
  types?: string[];
  groups?: string[];
  pages?: number[];
  search?: string;
}

export function filterMarkups(
  measurements: MeasurementLike[],
  filter: MarkupFilter,
): MeasurementLike[] {
  return measurements.filter((m) => {
    if (filter.types?.length && !filter.types.includes(m.type)) return false;
    if (filter.groups?.length && !filter.groups.includes(m.group)) return false;
    if (filter.pages?.length && !filter.pages.includes(m.page)) return false;
    if (filter.search) {
      const q = filter.search.toLowerCase();
      const hay = `${m.label} ${m.annotation} ${m.type} ${m.group} ${Object.values(m.customFields || {}).join(' ')}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
}

/* ── Totals ───────────────────────────────────────────────────── */

export interface TypeTotal {
  type: string;
  count: number;
  total: number;
  unit: string;
}

export function totalsByType(measurements: MeasurementLike[]): TypeTotal[] {
  const map = new Map<string, TypeTotal>();
  for (const m of measurements) {
    // Placed legends are UI chrome, not measured quantities — never counted
    // in type totals (or they'd also recurse into their own grouping).
    if (m.type === 'legend') continue;
    let t = map.get(m.type);
    if (!t) {
      t = { type: m.type, count: 0, total: 0, unit: m.unit };
      map.set(m.type, t);
    }
    t.count++;
    t.total += m.value;
  }
  return [...map.values()].sort((a, b) => a.type.localeCompare(b.type));
}
