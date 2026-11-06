import { describe, expect, it } from 'vitest';
import { comboOf, matchRevuShortcut, revuKeyForTool, REVU_SHORTCUTS } from './revu-shortcuts';

const ev = (code: string, key: string, mods: Partial<{ ctrlKey: boolean; shiftKey: boolean; altKey: boolean }> = {}) => ({
  code,
  key,
  ctrlKey: false,
  shiftKey: false,
  altKey: false,
  ...mods,
});

describe('revu shortcuts', () => {
  it('maps the Revu measurement keys', () => {
    expect(matchRevuShortcut(ev('KeyL', 'L', { shiftKey: true, altKey: true }))?.action).toEqual({ kind: 'tool', tool: 'distance' });
    expect(matchRevuShortcut(ev('KeyA', 'A', { shiftKey: true, altKey: true }))?.action).toEqual({ kind: 'tool', tool: 'area' });
    expect(matchRevuShortcut(ev('KeyC', 'C', { shiftKey: true, altKey: true }))?.action).toEqual({ kind: 'tool', tool: 'count' });
  });
  it('maps single-letter markup keys', () => {
    expect(matchRevuShortcut(ev('KeyL', 'l'))?.action).toEqual({ kind: 'tool', tool: 'line' });
    expect(matchRevuShortcut(ev('KeyA', 'a'))?.action).toEqual({ kind: 'tool', tool: 'arrow' });
    expect(matchRevuShortcut(ev('KeyQ', 'q'))?.action).toEqual({ kind: 'tool', tool: 'callout' });
  });
  it('maps view and panel keys', () => {
    expect(matchRevuShortcut(ev('Digit9', '9', { ctrlKey: true }))?.action).toEqual({ kind: 'cmd', cmd: 'fitPage' });
    expect(matchRevuShortcut(ev('KeyX', 'x', { altKey: true }))?.action).toEqual({ kind: 'cmd', cmd: 'panelToolChest' });
    expect(matchRevuShortcut(ev('BracketLeft', '{', { ctrlKey: true, shiftKey: true }))?.action).toEqual({ kind: 'cmd', cmd: 'sendToBack' });
    expect(comboOf(ev('ArrowRight', 'ArrowRight', { ctrlKey: true }))).toBe('Ctrl+Right');
    expect(comboOf(ev('Equal', '+', { shiftKey: true }))).toBe('+');
  });
  it('has no duplicate key bindings', () => {
    const keys = REVU_SHORTCUTS.map((s) => s.keys);
    expect(new Set(keys).size).toBe(keys.length);
  });
  it('prefers the measure key in tooltips', () => {
    expect(revuKeyForTool('distance')).toBe('Shift+Alt+L');
    expect(revuKeyForTool('line')).toBe('L');
  });
});
