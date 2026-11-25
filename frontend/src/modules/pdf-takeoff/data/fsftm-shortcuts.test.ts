import { describe, expect, it } from 'vitest';
import { comboOf, matchFSFTMShortcut, fsftmKeyForTool, FSFTM_SHORTCUTS } from './fsftm-shortcuts';

const ev = (code: string, key: string, mods: Partial<{ ctrlKey: boolean; shiftKey: boolean; altKey: boolean }> = {}) => ({
  code,
  key,
  ctrlKey: false,
  shiftKey: false,
  altKey: false,
  ...mods,
});

describe('fsftm shortcuts', () => {
  it('maps the FSFTM measurement keys', () => {
    expect(matchFSFTMShortcut(ev('KeyL', 'L', { shiftKey: true, altKey: true }))?.action).toEqual({ kind: 'tool', tool: 'distance' });
    expect(matchFSFTMShortcut(ev('KeyA', 'A', { shiftKey: true, altKey: true }))?.action).toEqual({ kind: 'tool', tool: 'area' });
    expect(matchFSFTMShortcut(ev('KeyC', 'C', { shiftKey: true, altKey: true }))?.action).toEqual({ kind: 'tool', tool: 'count' });
  });
  it('maps single-letter markup keys', () => {
    expect(matchFSFTMShortcut(ev('KeyL', 'l'))?.action).toEqual({ kind: 'tool', tool: 'line' });
    expect(matchFSFTMShortcut(ev('KeyA', 'a'))?.action).toEqual({ kind: 'tool', tool: 'arrow' });
    expect(matchFSFTMShortcut(ev('KeyQ', 'q'))?.action).toEqual({ kind: 'tool', tool: 'callout' });
  });
  it('maps view and panel keys', () => {
    expect(matchFSFTMShortcut(ev('Digit9', '9', { ctrlKey: true }))?.action).toEqual({ kind: 'cmd', cmd: 'fitPage' });
    expect(matchFSFTMShortcut(ev('KeyX', 'x', { altKey: true }))?.action).toEqual({ kind: 'cmd', cmd: 'panelToolChest' });
    expect(matchFSFTMShortcut(ev('BracketLeft', '{', { ctrlKey: true, shiftKey: true }))?.action).toEqual({ kind: 'cmd', cmd: 'sendToBack' });
    expect(comboOf(ev('ArrowRight', 'ArrowRight', { ctrlKey: true }))).toBe('Ctrl+Right');
    expect(comboOf(ev('Equal', '+', { shiftKey: true }))).toBe('+');
  });
  it('has no duplicate key bindings', () => {
    const keys = FSFTM_SHORTCUTS.map((s) => s.keys);
    expect(new Set(keys).size).toBe(keys.length);
  });
  it('prefers the measure key in tooltips', () => {
    expect(fsftmKeyForTool('distance')).toBe('Shift+Alt+L');
    expect(fsftmKeyForTool('line')).toBe('L');
  });
});
