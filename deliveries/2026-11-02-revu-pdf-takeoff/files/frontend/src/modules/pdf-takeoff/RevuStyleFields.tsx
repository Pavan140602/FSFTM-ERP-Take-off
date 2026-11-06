// OE-DELIVERY: 2026-11-02-revu-properties
/**
 * Revu-style property rows: colour, fill colour, line width, line style,
 * fill / line opacity and label mode. Used twice by the viewer:
 *  - "Tool properties" for the armed tool (style of the NEXT markup);
 *  - extra rows for the selected markup(s).
 * Every field is optional; ``fields`` picks which rows render.
 */
import { useTranslation } from 'react-i18next';
import { LABEL_MODES, LINE_STYLES, type LabelMode, type LineStyle, type ToolStyle } from './data/revu-style';

export type StyleField = 'color' | 'fillColor' | 'strokeWidth' | 'lineStyle' | 'fillAlpha' | 'strokeAlpha' | 'labelMode';

const SWATCHES = ['#EF4444', '#F97316', '#EAB308', '#22C55E', '#14B8A6', '#3B82F6', '#6366F1', '#A855F7', '#EC4899', '#111827'];

const LINE_STYLE_PREVIEW: Record<LineStyle, string> = {
  solid: '0',
  dashed: '6 4',
  dotted: '1 3',
  dashdot: '8 3 1 3',
};

export function RevuStyleFields({
  value,
  onChange,
  fields,
  testIdPrefix,
}: {
  value: ToolStyle;
  onChange: (patch: Partial<ToolStyle>) => void;
  fields: readonly StyleField[];
  testIdPrefix: string;
}) {
  const { t } = useTranslation();
  const has = (f: StyleField) => fields.includes(f);
  const reset = (patch: Partial<ToolStyle>, shown: boolean) =>
    shown ? (
      <button
        type="button"
        onClick={() => onChange(patch)}
        className="text-[10px] text-content-tertiary underline hover:text-content-primary"
      >
        {t('takeoff_viewer.reset', { defaultValue: 'Reset' })}
      </button>
    ) : null;
  const labelModeText: Record<LabelMode, string> = {
    all: t('takeoff_viewer.label_mode_all', { defaultValue: 'Name + value' }),
    value: t('takeoff_viewer.label_mode_value', { defaultValue: 'Value only' }),
    name: t('takeoff_viewer.label_mode_name', { defaultValue: 'Name only' }),
    none: t('takeoff_viewer.label_mode_none', { defaultValue: 'Hidden' }),
  };
  const lineStyleText: Record<LineStyle, string> = {
    solid: t('takeoff_viewer.line_solid', { defaultValue: 'Solid' }),
    dashed: t('takeoff_viewer.line_dashed', { defaultValue: 'Dashed' }),
    dotted: t('takeoff_viewer.line_dotted', { defaultValue: 'Dotted' }),
    dashdot: t('takeoff_viewer.line_dashdot', { defaultValue: 'Dash-dot' }),
  };

  const colorRow = (key: 'color' | 'fillColor', label: string) => (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs text-content-secondary">
        <span>{label}</span>
        {reset({ [key]: undefined }, value[key] != null)}
      </div>
      <div className="flex flex-wrap items-center gap-1">
        {SWATCHES.map((c) => (
          <button
            key={c}
            type="button"
            onClick={() => onChange({ [key]: c })}
            className={`h-5 w-5 rounded border ${value[key]?.toLowerCase() === c.toLowerCase() ? 'border-content-primary ring-2 ring-oe-blue/50' : 'border-border'}`}
            style={{ background: c }}
            aria-label={c}
          />
        ))}
        <input
          type="color"
          value={value[key] ?? '#3b82f6'}
          onChange={(e) => onChange({ [key]: e.target.value })}
          className="h-5 w-7 cursor-pointer rounded border border-border bg-transparent p-0"
          data-testid={`${testIdPrefix}-${key}`}
        />
      </div>
    </div>
  );

  return (
    <div className="space-y-3" data-testid={`${testIdPrefix}-fields`}>
      {has('color') && colorRow('color', t('takeoff_viewer.prop_line_color', { defaultValue: 'Colour' }))}
      {has('fillColor') && colorRow('fillColor', t('takeoff_viewer.prop_fill_color', { defaultValue: 'Fill colour' }))}

      {has('strokeWidth') && (
        <div className="space-y-1">
          <div className="flex items-center justify-between text-xs text-content-secondary">
            <span>{t('takeoff_viewer.prop_line_width', { defaultValue: 'Line width' })}</span>
            <span className="flex items-center gap-2">
              <span className="tabular-nums">{value.strokeWidth ?? 2} px</span>
              {reset({ strokeWidth: undefined }, value.strokeWidth != null)}
            </span>
          </div>
          <input
            type="range"
            min={0.5}
            max={20}
            step={0.5}
            value={value.strokeWidth ?? 2}
            onChange={(e) => onChange({ strokeWidth: Number(e.target.value) })}
            className="w-full"
            data-testid={`${testIdPrefix}-strokeWidth`}
          />
        </div>
      )}

      {has('lineStyle') && (
        <div className="space-y-1">
          <div className="text-xs text-content-secondary">{t('takeoff_viewer.prop_line_style', { defaultValue: 'Line style' })}</div>
          <div className="grid grid-cols-4 gap-1">
            {LINE_STYLES.map((ls) => (
              <button
                key={ls}
                type="button"
                onClick={() => onChange({ lineStyle: ls === 'solid' ? undefined : ls })}
                title={lineStyleText[ls]}
                className={`flex h-7 items-center justify-center rounded border ${(value.lineStyle ?? 'solid') === ls ? 'border-oe-blue bg-oe-blue/10' : 'border-border hover:bg-surface-secondary'}`}
                data-testid={`${testIdPrefix}-lineStyle-${ls}`}
              >
                <svg width="36" height="6" aria-hidden="true">
                  <line x1="1" y1="3" x2="35" y2="3" stroke="currentColor" strokeWidth="2" strokeDasharray={LINE_STYLE_PREVIEW[ls]} />
                </svg>
              </button>
            ))}
          </div>
        </div>
      )}

      {(['fillAlpha', 'strokeAlpha'] as const).filter(has).map((key) => (
        <div key={key} className="space-y-1">
          <div className="flex items-center justify-between text-xs text-content-secondary">
            <span>
              {key === 'fillAlpha'
                ? t('takeoff_viewer.prop_fill_opacity', { defaultValue: 'Fill opacity' })
                : t('takeoff_viewer.prop_stroke_opacity', { defaultValue: 'Line opacity' })}
            </span>
            <span className="flex items-center gap-2">
              <span className="tabular-nums">{Math.round((value[key] ?? (key === 'fillAlpha' ? 0.15 : 1)) * 100)}%</span>
              {reset({ [key]: undefined }, value[key] != null)}
            </span>
          </div>
          <input
            type="range"
            min={0}
            max={100}
            step={5}
            value={Math.round((value[key] ?? (key === 'fillAlpha' ? 0.15 : 1)) * 100)}
            onChange={(e) => onChange({ [key]: Number(e.target.value) / 100 })}
            className="w-full"
            data-testid={`${testIdPrefix}-${key}`}
          />
        </div>
      ))}

      {has('labelMode') && (
        <div className="space-y-1">
          <div className="text-xs text-content-secondary">{t('takeoff_viewer.prop_label_mode', { defaultValue: 'Label on drawing' })}</div>
          <select
            value={value.labelMode ?? ''}
            onChange={(e) => onChange({ labelMode: (e.target.value || undefined) as LabelMode | undefined })}
            className="h-7 w-full rounded border border-border bg-surface-secondary px-2 text-xs text-content-primary"
            data-testid={`${testIdPrefix}-labelMode`}
          >
            <option value="">{t('takeoff_viewer.label_mode_default', { defaultValue: 'Default (Colours tab)' })}</option>
            {LABEL_MODES.map((lm) => (
              <option key={lm} value={lm}>{labelModeText[lm]}</option>
            ))}
          </select>
        </div>
      )}
    </div>
  );
}
