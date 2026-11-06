// OE-DELIVERY: 2026-11-07-text-box
/**
 * Text Box properties bar, like Revu's text toolbar: font, size, bold /
 * italic / underline / strike-through, alignment, text colour, fill, border
 * and opacity. Floats over the sheet above the text box being edited or
 * selected, and sets the default for new boxes when the Text Box tool is
 * active with nothing selected.
 *
 * Every control keeps focus off itself where it can (buttons use
 * onMouseDown preventDefault) so typing in the box is not interrupted; the
 * editor treats a blur into this bar as "still editing".
 */
import { AlignCenter, AlignLeft, AlignRight, Bold, Italic, Strikethrough, Underline } from 'lucide-react';
import type { BorderStyle, TextAlign, TextStyle } from '../data/text-box';
import { TEXT_FONTS, TEXT_SIZES } from '../data/text-box';
import ColorPicklist from './ColorPicklist';

export interface TextFormatBarProps {
  style: TextStyle;
  /** Colour the text follows when it has none of its own. */
  markupColour: string;
  onChange: (patch: Partial<TextStyle>) => void;
  /** What the bar applies to, shown at its start. */
  caption?: string;
}

const keep = (e: React.MouseEvent) => e.preventDefault();

function Toggle({ on, title, onClick, children, testId }: { on: boolean; title: string; onClick: () => void; children: React.ReactNode; testId: string }) {
  return (
    <button
      type="button"
      title={title}
      aria-pressed={on}
      onMouseDown={keep}
      onClick={onClick}
      data-testid={testId}
      className={`flex h-6 w-6 items-center justify-center rounded ${on ? 'bg-oe-blue/15 text-oe-blue' : 'text-content-secondary hover:bg-surface-secondary'}`}
    >
      {children}
    </button>
  );
}

function Swatch({ value, title, onPick, testId, none }: { value: string | null; title: string; onPick: (v: string | null) => void; testId: string; none?: boolean }) {
  // Revu-style colour picklist (OE-DELIVERY 2026-11-08-stud-walls).
  return <ColorPicklist value={value} onChange={onPick} allowNone={none} title={title} testId={testId} />;
}

export function NativeSwatch({ value, title, onPick, testId, none }: { value: string | null; title: string; onPick: (v: string | null) => void; testId: string; none?: boolean }) {
  return (
    <span className="flex items-center gap-0.5" title={title}>
      <label className="relative h-5 w-5 cursor-pointer overflow-hidden rounded border border-border" data-testid={testId}>
        <span className="absolute inset-0" style={value ? { background: value } : { background: 'repeating-linear-gradient(45deg,#fff 0 3px,#e5e7eb 3px 6px)' }} />
        <input
          type="color"
          className="absolute inset-0 cursor-pointer opacity-0"
          value={value ?? '#ffffff'}
          onChange={(e) => onPick(e.target.value)}
        />
      </label>
      {none && (
        <button
          type="button"
          onMouseDown={keep}
          onClick={() => onPick(null)}
          title={`No ${title.toLowerCase()}`}
          className={`rounded px-1 text-[10px] ${value === null ? 'bg-oe-blue/15 text-oe-blue' : 'text-content-tertiary hover:bg-surface-secondary'}`}
          data-testid={`${testId}-none`}
        >
          none
        </button>
      )}
    </span>
  );
}

export default function TextFormatBar({ style, markupColour, onChange, caption }: TextFormatBarProps) {
  const textColour = style.color || markupColour;
  const border = style.border === undefined ? textColour : style.border;
  const sep = <span className="mx-0.5 h-5 w-px bg-border" />;
  return (
    <div
      className="flex flex-wrap items-center gap-1 rounded-md border border-border bg-surface-elevated px-1.5 py-1 text-[11px] text-content-primary shadow-lg"
      data-testid="text-format-bar"
      data-text-format-bar=""
      onMouseDown={(e) => e.stopPropagation()}
      onClick={(e) => e.stopPropagation()}
    >
      {caption && <span className="pr-1 font-semibold text-content-secondary">{caption}</span>}
      <select
        value={TEXT_FONTS.includes(style.font as (typeof TEXT_FONTS)[number]) ? style.font : 'Arial'}
        onChange={(e) => onChange({ font: e.target.value })}
        className="h-6 rounded border border-border bg-surface-primary px-1"
        style={{ fontFamily: style.font }}
        title="Font"
        data-testid="text-font"
      >
        {TEXT_FONTS.map((f) => (
          <option key={f} value={f} style={{ fontFamily: f }}>
            {f}
          </option>
        ))}
      </select>
      <input
        list="text-box-sizes"
        type="number"
        min={2}
        max={400}
        step={0.5}
        value={style.size}
        onChange={(e) => {
          const v = Number(e.target.value);
          if (v >= 2 && v <= 400) onChange({ size: v });
        }}
        className="h-6 w-14 rounded border border-border bg-surface-primary px-1"
        title="Font size (pt)"
        data-testid="text-size"
      />
      <datalist id="text-box-sizes">
        {TEXT_SIZES.map((s) => (
          <option key={s} value={s} />
        ))}
      </datalist>
      {sep}
      <Toggle on={style.bold} title="Bold (Ctrl+B)" onClick={() => onChange({ bold: !style.bold })} testId="text-bold">
        <Bold size={13} />
      </Toggle>
      <Toggle on={style.italic} title="Italic (Ctrl+I)" onClick={() => onChange({ italic: !style.italic })} testId="text-italic">
        <Italic size={13} />
      </Toggle>
      <Toggle on={style.underline} title="Underline (Ctrl+U)" onClick={() => onChange({ underline: !style.underline })} testId="text-underline">
        <Underline size={13} />
      </Toggle>
      <Toggle on={style.strike} title="Strike-through" onClick={() => onChange({ strike: !style.strike })} testId="text-strike">
        <Strikethrough size={13} />
      </Toggle>
      {sep}
      {(['left', 'center', 'right'] as TextAlign[]).map((a) => (
        <Toggle key={a} on={style.align === a} title={`Align ${a}`} onClick={() => onChange({ align: a })} testId={`text-align-${a}`}>
          {a === 'left' ? <AlignLeft size={13} /> : a === 'center' ? <AlignCenter size={13} /> : <AlignRight size={13} />}
        </Toggle>
      ))}
      {sep}
      <span className="text-content-tertiary">Text</span>
      <Swatch value={textColour} title="Text colour" onPick={(v) => onChange({ color: v ?? undefined })} testId="text-colour" />
      <span className="text-content-tertiary">Fill</span>
      <Swatch value={style.fill} title="Fill" onPick={(v) => onChange({ fill: v })} testId="text-fill" none />
      {style.fill && (
        <input
          type="range"
          min={5}
          max={100}
          value={Math.round(style.fillAlpha * 100)}
          onChange={(e) => onChange({ fillAlpha: Number(e.target.value) / 100 })}
          className="w-14"
          title={`Fill opacity ${Math.round(style.fillAlpha * 100)} %`}
          data-testid="text-fill-alpha"
        />
      )}
      <span className="text-content-tertiary">Border</span>
      <Swatch value={border} title="Border" onPick={(v) => onChange({ border: v })} testId="text-border" none />
      {border && (
        <>
          <select
            value={style.borderWidth}
            onChange={(e) => onChange({ borderWidth: Number(e.target.value) })}
            className="h-6 rounded border border-border bg-surface-primary px-0.5"
            title="Border width (pt)"
            data-testid="text-border-width"
          >
            {[0.5, 1, 1.5, 2, 3, 4, 6].map((w) => (
              <option key={w} value={w}>
                {w} pt
              </option>
            ))}
          </select>
          <select
            value={style.borderStyle}
            onChange={(e) => onChange({ borderStyle: e.target.value as BorderStyle })}
            className="h-6 rounded border border-border bg-surface-primary px-0.5"
            title="Border style"
            data-testid="text-border-style"
          >
            <option value="solid">Solid</option>
            <option value="dashed">Dashed</option>
            <option value="dotted">Dotted</option>
            <option value="cloud">Cloud</option>
          </select>
        </>
      )}
      {sep}
      <span className="text-content-tertiary">Opacity</span>
      <input
        type="range"
        min={10}
        max={100}
        value={Math.round(style.opacity * 100)}
        onChange={(e) => onChange({ opacity: Number(e.target.value) / 100 })}
        className="w-14"
        title={`Opacity ${Math.round(style.opacity * 100)} %`}
        data-testid="text-opacity"
      />
    </div>
  );
}
