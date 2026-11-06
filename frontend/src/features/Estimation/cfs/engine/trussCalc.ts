// DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
// Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
/**
 * Truss geometry engine — TypeScript port of the workbook's Floor/Roof
 * Trusses sheet formulas (the LET formulas in cols P..W / L..S) plus the
 * two VBA behaviours on the Roof sheet:
 *
 *  - Worksheet_Change attic recalc → calcAttic() below (the workbook runs a
 *    panel-by-panel loop because the formula columns cannot express it).
 *    Note: the workbook's S/T formulas read col 14 (Notes) for the attic
 *    flag, which never equals "Yes" — so they would compute *standard*
 *    verticals for an Attic Truss and rely on VBA overwriting the cells.
 *    This engine instead keys off the Rule Table's real Use_Attic_Opening
 *    flag (col 8), i.e. it always does what the VBA intended.
 *  - ShowCalcDetail → trussCalcDetail() — the per-member audit trail.
 *
 * Column letters in comments refer to the Roof Trusses sheet; the Floor
 * sheet uses the same formulas with shifted columns (verified identical).
 */

import { FASTENERS } from '../data/fasteners';
import type { TrussRule } from '../data/ruleTable';
import { gaugeFromMil, matchTrussMaterial, matchTrussType, milThickness, norm } from './matchers';
import { err, ok, type CalcResult, type Cell, type TrussRowComputed, type TrussRowInput } from './types';

const roundUp = (x: number): number => Math.ceil(x);
const isYes = (v: string | null | undefined): boolean => (v ?? '').trim().toLowerCase() === 'yes';

function num(v: number | null | undefined): number | null {
  return typeof v === 'number' && Number.isFinite(v) ? v : null;
}

function missing(...names: string[]): string[] {
  return names.map((n) => `${n} is required`);
}

/** Panel loop shared by the pitched-truss groups. */
interface PanelGeom {
  /** vertical length per panel point, ridge-outward */
  v: number[];
  /** panel widths (last panel may be shorter) */
  pw: number[];
  vRidge: number;
}

function pitchedPanels(sp: number, ps: number, sr: number, fascia: number, bcSlope: number | null, useBc: boolean): PanelGeom {
  const fp = roundUp(sp / ps);
  const lp = sp - (fp - 1) * ps;
  const v: number[] = [];
  const pw: number[] = [];
  for (let n = 1; n <= fp; n++) {
    const dist = Math.max(sp - n * ps, 0);
    const tc = dist * (sr / 12) + fascia;
    const bc = useBc && bcSlope != null ? dist * (bcSlope / 12) : 0;
    v.push(tc - bc);
    pw.push(n === fp ? lp : ps);
  }
  const tcRidge = sp * (sr / 12) + fascia;
  const bcRidge = useBc && bcSlope != null ? sp * (bcSlope / 12) : 0;
  return { v, pw, vRidge: tcRidge - bcRidge };
}

/** VBA Worksheet_Change attic recalc, ported 1:1. */
function calcAttic(span: number, sr: number, fascia: number, ps: number, aoW: number, aoH: number): { vert: number; diag: number } {
  const hs = span / 2;
  const aoHalf = aoW / 2;
  const zA = hs - aoHalf;
  const zC = aoHalf;
  const riserH = hs * (sr / 12) + fascia;
  const centerV = riserH - aoH;
  const fpA = roundUp(zA / ps);
  const lpA = zA - (fpA - 1) * ps;
  const fpC = roundUp(zC / ps);
  const lpC = zC - (fpC - 1) * ps;

  let totalV = aoH * 2;
  let totalD = 0;
  // Zone A — attic wall outward, both sides x2
  for (let n = 1; n <= fpA; n++) {
    const pw = n === fpA ? lpA : ps;
    const bearD = Math.max(zA - n * ps, 0);
    const vN = bearD * (sr / 12) + fascia;
    totalV += vN * 2;
    totalD += Math.sqrt(vN * vN + pw * pw) * 2;
  }
  // Zone B — clear attic opening
  totalV += aoH * 2 + centerV;
  totalD += aoW;
  // Zone C — riser outward above the attic, both sides x2
  for (let n = 1; n <= fpC - 1; n++) {
    const pw = n === fpC - 1 ? lpC : ps;
    const distR = Math.min(n * ps, zC);
    const tcC = (hs - distR) * (sr / 12) + fascia;
    const vC = tcC - aoH;
    totalV += vC * 2;
    totalD += Math.sqrt(vC * vC + pw * pw) * 2;
  }
  return { vert: totalV, diag: totalD };
}

function calcPanels(rule: TrussRule, span: number | null, ps: number | null): CalcResult<Cell> {
  if (!isYes(rule.generatesPanels)) return ok(0);
  if (span == null || span <= 0) return err(null, ...missing('Length'));
  if (ps == null || ps <= 0) return err(null, ...missing('Panel spacing'));
  return ok(isYes(rule.symmetric) ? roundUp(span / 2 / ps) * 2 : roundUp(span / ps));
}

function calcTC(rule: TrussRule, r: TrussRowInput): CalcResult<Cell> {
  const D = num(r.lengthFt);
  const F = num(r.slope);
  const G = num(r.fasciaFt);
  const L = num(r.flatLengthFt);
  if (D == null || D <= 0) return err(null, ...missing('Length'));
  const sym = isYes(rule.symmetric);
  const useFL = isYes(rule.useFlatLength);
  if (rule.category === 'Roof' || rule.geometry === 'Flat') {
    // IF(OR(F="",F=0), D, SQRT(D^2+(D*(F/12))^2))
    if (F == null || F === 0) return ok(D);
    return ok(Math.sqrt(D * D + Math.pow(D * (F / 12), 2)));
  }
  if (rule.category === 'Truss') {
    if (F == null || F === 0) return err(null, ...missing('Slope ratio'));
    if (sym) {
      if (useFL) {
        // Hip Step Down: (SQRT((D-L)^2/4+((D-L)/2*(F/12))^2)+G)*2+L
        if (L == null || L <= 0) return err(null, ...missing('Flat length'));
        const g = G ?? 0;
        const jack = D - L;
        return ok((Math.sqrt((jack * jack) / 4 + Math.pow((jack / 2) * (F / 12), 2)) + g) * 2 + L);
      }
      // (SQRT(D^2/4+(D/2*(F/12))^2)+G)*2
      const g = G ?? 0;
      return ok((Math.sqrt((D * D) / 4 + Math.pow((D / 2) * (F / 12), 2)) + g) * 2);
    }
    // mono: SQRT(D^2+(D*(F/12))^2)+G
    return ok(Math.sqrt(D * D + Math.pow(D * (F / 12), 2)) + (G ?? 0));
  }
  return err(null, `No chord rule for "${rule.type}"`);
}

function calcBC(rule: TrussRule, r: TrussRowInput): CalcResult<Cell> {
  const D = num(r.lengthFt);
  const F = num(r.slope);
  const I = num(r.bcSlope);
  if (D == null || D <= 0) return err(null, ...missing('Length'));
  if (rule.category === 'Roof') return ok(0);
  if (rule.category === 'Truss') {
    if (isYes(rule.useBcSlope)) {
      // Scissor: SQRT(D^2+(D*(I/12))^2)
      if (I == null || I === 0) return err(null, ...missing('BC slope'));
      return ok(Math.sqrt(D * D + Math.pow(D * (I / 12), 2)));
    }
    if (rule.geometry === 'Flat') {
      if (F == null || F === 0) return ok(D);
      return ok(Math.sqrt(D * D + Math.pow(D * (F / 12), 2)));
    }
    return ok(D);
  }
  return err(null, `No chord rule for "${rule.type}"`);
}

interface VertDiag {
  vert: CalcResult<Cell>;
  diag: CalcResult<Cell>;
}

function calcVertDiag(rule: TrussRule, r: TrussRowInput): VertDiag {
  const D = num(r.lengthFt);
  const F = num(r.slope);
  const G = num(r.fasciaFt);
  const H = num(r.panelSpacingFt);
  const I = num(r.bcSlope);
  const J = num(r.atticWidthFt);
  const K = num(r.atticHeightFt);
  const L = num(r.flatLengthFt);
  const sym = isYes(rule.symmetric);
  const useBCS = isYes(rule.useBcSlope);
  const useFL = isYes(rule.useFlatLength);

  if (rule.category === 'Roof') return { vert: ok(0), diag: ok(0) };

  // Attic Truss → the VBA panel loop (see module docstring for why).
  if (isYes(rule.useAtticOpening)) {
    if (D == null || D <= 0 || H == null || H <= 0) {
      const e = [...missing('Length'), ...missing('Panel spacing')].filter((_, i, a) => a.indexOf(_) === i);
      return { vert: err(null, ...e), diag: err(null, ...e) };
    }
    if (F == null || F === 0) return { vert: err(null, ...missing('Slope ratio')), diag: err(null, ...missing('Slope ratio')) };
    if (J == null || J <= 0 || K == null || K <= 0) {
      return { vert: err(null, ...missing('Attic width', 'Attic height')), diag: err(null, ...missing('Attic width', 'Attic height')) };
    }
    const { vert, diag } = calcAttic(D, F, G ?? 0, H, J, K);
    return { vert: ok(vert), diag: ok(diag) };
  }

  if (D == null || D <= 0) return { vert: err(null, ...missing('Length')), diag: err(null, ...missing('Length')) };
  if (H == null || H <= 0) return { vert: err(null, ...missing('Panel spacing')), diag: err(null, ...missing('Panel spacing')) };

  // Flat geometry — Group 6
  if (rule.geometry === 'Flat') {
    const depth = G ?? 0;
    const sm = Math.sqrt(1 + Math.pow((F ?? 0) / 12, 2));
    const sspan = D * sm;
    const fp = roundUp(sspan / H);
    const lp = sspan - (fp - 1) * H;
    const vert = norm(rule.type) === norm('Flat Truss') ? depth * 2 : (fp + 1) * depth;
    let diag = 0;
    for (let n = 1; n <= fp; n++) {
      const pw = n === fp ? lp : H;
      diag += Math.sqrt(depth * depth + pw * pw);
    }
    return { vert: ok(vert), diag: ok(diag) };
  }

  // Hip Step Down — Group 7
  if (useFL) {
    if (L == null || L <= 0) return { vert: err(null, ...missing('Flat length')), diag: err(null, ...missing('Flat length')) };
    if (F == null || F === 0) return { vert: err(null, ...missing('Slope ratio')), diag: err(null, ...missing('Slope ratio')) };
    const jackSpan = (D - L) / 2;
    const riserH = jackSpan * (F / 12) + (G ?? 0);
    const fpJ = roundUp(jackSpan / H);
    const lpJ = jackSpan - (fpJ - 1) * H;
    let jackVert = riserH;
    let jackDiag = 0;
    for (let n = 1; n <= fpJ; n++) {
      const distJ = Math.max(jackSpan - n * H, 0);
      const vJ = distJ * (F / 12) + (G ?? 0);
      const pwJ = n === fpJ ? lpJ : H;
      jackVert += vJ;
      jackDiag += Math.sqrt(vJ * vJ + pwJ * pwJ);
    }
    const fpF = roundUp(L / H);
    const lpF = L - (fpF - 1) * H;
    const flatVert = (fpF + 1) * riserH;
    let flatDiag = 0;
    for (let n = 1; n <= fpF; n++) {
      const pwF = n === fpF ? lpF : H;
      flatDiag += Math.sqrt(riserH * riserH + pwF * pwF);
    }
    return { vert: ok(jackVert * 2 + flatVert), diag: ok(jackDiag * 2 + flatDiag) };
  }

  // Pitched groups 1–4
  const vert: CalcResult<Cell> = (() => {
    if (!isYes(rule.hasVertical)) return ok<Cell>(0);
    if (F == null || F === 0) return err<Cell>(null, ...missing('Slope ratio'));
    const sp = sym ? D / 2 : D;
    const { v, vRidge } = pitchedPanels(sp, H, F, G ?? 0, I, useBCS);
    const sum = v.reduce((a, b) => a + b, 0);
    return ok(sym ? vRidge + sum * 2 : vRidge + sum);
  })();
  const diag: CalcResult<Cell> = (() => {
    if (!isYes(rule.hasDiagonal)) return ok<Cell>(0);
    if (F == null || F === 0) return err<Cell>(null, ...missing('Slope ratio'));
    const sp = sym ? D / 2 : D;
    const { v, pw } = pitchedPanels(sp, H, F, G ?? 0, I, useBCS);
    const sum = v.reduce((a, vn, i) => a + Math.sqrt(vn * vn + (pw[i] ?? 0) * (pw[i] ?? 0)), 0);
    return ok(sym ? sum * 2 : sum);
  })();
  return { vert, diag };
}

function screwSpecFor(r: TrussRowInput, kind: 'floor' | 'roof', rule: TrussRule | null): string | null {
  if (!r.material?.trim()) return null;
  if (kind === 'floor' && (!rule || rule.category !== 'Truss')) return '0';
  const gauge = gaugeFromMil(milThickness(r.material));
  if (gauge == null) return '—';
  const f = FASTENERS.find((x) => x.gauge === gauge);
  if (!f) return '—';
  // NOTE: the workbook does NOT trim the Length value (' 3/4"'), so neither do we.
  return `${f.minScrew ?? '—'}x${f.length ?? '—'} TEK`;
}

function screwQtyFor(r: TrussRowInput, kind: 'floor' | 'roof', rule: TrussRule | null, panels: Cell, tc: Cell): Cell {
  const D = num(r.lengthFt);
  const H = num(r.panelSpacingFt);
  const E = num(r.qty);
  const stc = num(r.stiffTC) ?? 0;
  const sbc = num(r.stiffBC) ?? 0;
  if (!rule || rule.category !== 'Truss') return 0;
  if (D == null || D <= 0 || H == null || H <= 0 || E == null) return null;
  const tcN = typeof tc === 'number' ? tc : 0;
  const xtc = stc > 0 ? roundUp(tcN / 2) * 2 * stc : 0;
  // BC LNFT is needed for the xbc term — recompute cheaply via calcBC
  const bcRes = calcBC(rule, r);
  const bcN = typeof bcRes.value === 'number' ? bcRes.value : 0;
  const xbc = sbc > 0 ? roundUp(bcN / 2) * 2 * sbc : 0;

  let mems: number;
  if (kind === 'floor') {
    const p = typeof panels === 'number' ? panels : 0;
    mems = isYes(rule.hasVertical) ? 2 * p + 1 : p + 2;
  } else {
    const fpHalf = roundUp(D / 2 / H);
    const fpFull = roundUp(D / H);
    const useFL = isYes(rule.useFlatLength);
    const L = num(r.flatLengthFt) ?? 0;
    const J = num(r.atticWidthFt) ?? 0;
    const fpJ = useFL ? roundUp((D - L) / 2 / H) : 0;
    const fpF = useFL ? roundUp(L / H) : 0;
    const fpA = norm(rule.type) === norm('Attic Truss') ? roundUp((D / 2 - J / 2) / H) : 0;
    const fpCC = norm(rule.type) === norm('Attic Truss') ? roundUp(J / 2 / H) : 0;
    if (norm(rule.type) === norm('Attic Truss')) mems = 4 * (fpA + fpCC) + 8;
    else if (useFL) mems = 4 * fpJ + 2 * fpF + 1;
    else if (rule.geometry === 'Dual_Slope') mems = isYes(rule.hasVertical) ? 4 * fpHalf + 1 : 2 * fpHalf + 2;
    else if (isYes(rule.hasVertical)) mems = 2 * fpFull + 1;
    else mems = fpFull + 2;
  }
  return (mems * 8 + xtc + xbc) * E;
}

/**
 * Full row calc — mirrors the workbook's auto-calculated columns.
 * `kind` selects the Floor vs Roof sheet's screw semantics.
 */
export function calcTrussRow(r: TrussRowInput, kind: 'floor' | 'roof'): TrussRowComputed {
  const errors: string[] = [];
  if (!r.memberType?.trim()) {
    return {
      rule: null, ruleError: null, panels: null, tcLnft: null, bcLnft: null,
      vertLnft: null, diagLnft: null, memberLnft: null, totalLnft: null,
      weightLb: null, screwSpec: null, screwQty: null, materialCost: null,
      totalCost: null, errors,
    };
  }
  const rule = matchTrussType(r.memberType);
  if (!rule) {
    const msg = `'${r.memberType.trim()}' is not a valid type — check the Rule Table`;
    return {
      rule: null, ruleError: msg, panels: null, tcLnft: null, bcLnft: null,
      vertLnft: null, diagLnft: null, memberLnft: null, totalLnft: null,
      weightLb: null, screwSpec: null, screwQty: null, materialCost: null,
      totalCost: null, errors: [msg],
    };
  }

  const panels = calcPanels(rule, num(r.lengthFt), num(r.panelSpacingFt));
  const tc = calcTC(rule, r);
  const bc = calcBC(rule, r);
  const { vert, diag } = calcVertDiag(rule, r);
  errors.push(...panels.errors, ...tc.errors, ...bc.errors, ...vert.errors, ...diag.errors);

  const tcN = typeof tc.value === 'number' ? tc.value : null;
  const bcN = typeof bc.value === 'number' ? bc.value : null;
  const vN = typeof vert.value === 'number' ? vert.value : null;
  const dN = typeof diag.value === 'number' ? diag.value : null;
  const stc = num(r.stiffTC) ?? 0;
  const sbc = num(r.stiffBC) ?? 0;
  const sweb = num(r.stiffWeb) ?? 0;

  // (TC*(1+stc)) + (BC*(1+sbc)) + (vert+diag) + sweb
  let memberLnft: Cell = null;
  if (tcN != null && bcN != null && vN != null && dN != null) {
    memberLnft = tcN * (1 + stc) + bcN * (1 + sbc) + (vN + dN) + sweb;
  } else {
    errors.push('Member length needs TC, BC, verticals and diagonals');
  }

  const qty = num(r.qty);
  const totalLnft: Cell = typeof memberLnft === 'number' && qty != null ? memberLnft * qty : null;

  let weightLb: Cell = null;
  if (typeof totalLnft === 'number') {
    if (!r.material?.trim()) {
      errors.push('Material is required for weight');
    } else {
      const mat = matchTrussMaterial(r.material);
      if (!mat || mat.weightLbFt == null) {
        errors.push(`Material '${r.material.trim()}' not found in Reference Sheet`);
      } else {
        weightLb = totalLnft * mat.weightLbFt;
      }
    }
  }

  const screwSpec = screwSpecFor(r, kind, rule);
  const screwQty = screwQtyFor(r, kind, rule, panels.value, tc.value);

  // Costing — the workbook leaves these columns blank; the app prices them.
  const mat = r.material?.trim() ? matchTrussMaterial(r.material) : null;
  const defaultPrice = kind === 'roof' ? mat?.trussPrice ?? null : mat?.trussPrice ?? mat?.joistPrice ?? null;
  const pricePerFt = num(r.pricePerFt) ?? defaultPrice ?? 0;
  const materialCost: Cell = typeof totalLnft === 'number' ? totalLnft * pricePerFt : null;
  const connectorCost = num(r.connectorCost) ?? 0;
  const totalCost: Cell = typeof materialCost === 'number' ? materialCost + connectorCost : null;

  return {
    rule: rule.type, ruleError: null,
    panels: panels.value, tcLnft: tc.value, bcLnft: bc.value,
    vertLnft: vert.value, diagLnft: diag.value,
    memberLnft, totalLnft, weightLb, screwSpec, screwQty,
    materialCost, totalCost,
    errors: [...new Set(errors)],
  };
}

/**
 * Calculation detail — the ShowCalcDetail VBA popup, as data.
 * Returns the same per-member lines (V1… Vn, D1… Dn) the macro shows.
 */
export function trussCalcDetail(r: TrussRowInput): string[] {
  const lines: string[] = [];
  const rule = matchTrussType(r.memberType);
  if (!rule) return [`'${r.memberType}' is not a valid type.`];
  const D = num(r.lengthFt) ?? 0;
  const F = num(r.slope) ?? 0;
  const G = num(r.fasciaFt) ?? 0;
  const H = num(r.panelSpacingFt) ?? 0;
  if (D <= 0 || H <= 0) return ['Length and panel spacing are required.'];
  const f2 = (x: number): string => x.toFixed(2);

  lines.push(`Truss Type    : ${rule.type}`);
  lines.push(`Span          : ${D} ft`);
  lines.push(`Slope Ratio   : ${F}:12`);
  lines.push(`Panel Spacing : ${H} ft`);
  lines.push(`Fascia        : ${G} ft`);

  const useBCS = isYes(rule.useBcSlope);
  const I = num(r.bcSlope);

  if (isYes(rule.useAtticOpening)) {
    const J = num(r.atticWidthFt) ?? 0;
    const K = num(r.atticHeightFt) ?? 0;
    const hs = D / 2;
    const zA = hs - J / 2;
    const zC = J / 2;
    const riserH = hs * (F / 12) + G;
    lines.push(`Attic Width   : ${J} ft   Attic Height : ${K} ft`);
    lines.push(`Zone A (bearing→attic wall): ${f2(zA)} ft   Zone C (attic wall→riser): ${f2(zC)} ft`);
    lines.push(`Riser Height  : ${f2(riserH)} ft   Center V: ${f2(riserH - K)} ft`);
    const fpA = roundUp(zA / H);
    for (let n = 1; n <= fpA; n++) {
      const bearD = Math.max(zA - n * H, 0);
      const vN = bearD * (F / 12) + G;
      lines.push(`V${n} (x2): (${f2(bearD)} x ${F}/12)+${G} = ${f2(vN)} ft  x2 = ${f2(vN * 2)} ft`);
    }
    lines.push(`V_attic (x2): ${f2(K)} ft  x2 = ${f2(K * 2)} ft   + center ${f2(riserH - K)} ft (once)`);
    return lines;
  }

  if (rule.geometry === 'Flat') {
    const sm = Math.sqrt(1 + Math.pow(F / 12, 2));
    const sspan = D * sm;
    const fp = roundUp(sspan / H);
    const lp = sspan - (fp - 1) * H;
    lines.push(`Sloped span   : ${f2(sspan)} ft   Depth: ${G} ft   Panels: ${fp} (last ${f2(lp)} ft)`);
    if (norm(rule.type) === norm('Flat Truss')) {
      lines.push(`V_start: ${f2(G)} ft   V_end: ${f2(G)} ft   (end verticals only)`);
    } else {
      lines.push(`Verticals: ${fp + 1} x ${f2(G)} ft (all panel points)`);
    }
    for (let n = 1; n <= fp; n++) {
      const pw = n === fp ? lp : H;
      lines.push(`D${n}: SQRT(${f2(G)}^2+${f2(pw)}^2) = ${f2(Math.sqrt(G * G + pw * pw))} ft`);
    }
    return lines;
  }

  if (isYes(rule.useFlatLength)) {
    const L = num(r.flatLengthFt) ?? 0;
    const jackSpan = (D - L) / 2;
    const riserH = jackSpan * (F / 12) + G;
    lines.push(`Jack span     : ${f2(jackSpan)} ft each side   Flat: ${L} ft   Ridge: ${f2(riserH)} ft`);
    const fpJ = roundUp(jackSpan / H);
    for (let n = 1; n <= fpJ; n++) {
      const distJ = Math.max(jackSpan - n * H, 0);
      const vJ = distJ * (F / 12) + G;
      lines.push(`V${n} (x2): (${f2(distJ)} x ${F}/12)+${G} = ${f2(vJ)} ft  x2 = ${f2(vJ * 2)} ft`);
    }
    lines.push(`Flat verticals: ${roundUp(L / H) + 1} x ${f2(riserH)} ft`);
    return lines;
  }

  const sym = isYes(rule.symmetric);
  const sp = sym ? D / 2 : D;
  lines.push(`Half span     : ${f2(sp)} ft   Panels/side: ${roundUp(sp / H)}`);
  if (useBCS && I != null) lines.push(`BC Slope      : ${I}:12`);
  const { v, pw, vRidge } = pitchedPanels(sp, H, F, G, I, useBCS);
  if (isYes(rule.hasVertical)) {
    lines.push(`V_ridge: ${f2(vRidge)} ft${sym ? ' (once)' : ''}`);
    v.forEach((vn, i) => {
      lines.push(`V${i + 1}${sym ? ' (x2)' : ''}: ${f2(vn)} ft${sym ? `  x2 = ${f2(vn * 2)} ft` : ''}`);
    });
  } else {
    lines.push('Verticals: none');
  }
  if (isYes(rule.hasDiagonal)) {
    v.forEach((vn, i) => {
      const pwi = pw[i] ?? 0;
      const dn = Math.sqrt(vn * vn + pwi * pwi);
      lines.push(`D${i + 1}${sym ? ' (x2)' : ''}: SQRT(${f2(vn)}^2+${f2(pwi)}^2) = ${f2(dn)} ft${sym ? `  x2 = ${f2(dn * 2)} ft` : ''}`);
    });
  }
  return lines;
}
