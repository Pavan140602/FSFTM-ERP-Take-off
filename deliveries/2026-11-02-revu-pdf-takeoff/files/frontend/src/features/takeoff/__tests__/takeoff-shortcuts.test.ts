// DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
// Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
import { describe, it, expect } from 'vitest';
import {
  TOOL_SHORTCUT_MAP,
  SHORTCUT_LETTER,
  shortcutToTool,
  labelWithShortcut,
  shouldHandleShortcut,
} from '../lib/takeoff-shortcuts';

describe('takeoff-shortcuts', () => {
  describe('shortcutToTool', () => {
    it('maps V → select', () => {
      expect(shortcutToTool('V')).toBe('select');
      expect(shortcutToTool('v')).toBe('select');
    });

    it('maps the Revu single-key tool letters', () => {
      expect(shortcutToTool('L')).toBe('line');
      expect(shortcutToTool('A')).toBe('arrow');
      expect(shortcutToTool('R')).toBe('rectangle');
      expect(shortcutToTool('E')).toBe('ellipse');
      expect(shortcutToTool('C')).toBe('cloud');
      expect(shortcutToTool('T')).toBe('text');
      expect(shortcutToTool('Q')).toBe('callout');
      expect(shortcutToTool('H')).toBe('highlight');
      expect(shortcutToTool('P')).toBe('pen');
    });

    it('returns null for unmapped keys', () => {
      expect(shortcutToTool('Z')).toBeNull();
      expect(shortcutToTool('1')).toBeNull();
      expect(shortcutToTool('Escape')).toBeNull();
      expect(shortcutToTool('')).toBeNull();
    });

    it('is case-insensitive', () => {
      expect(shortcutToTool('l')).toBe(shortcutToTool('L'));
      expect(shortcutToTool('c')).toBe(shortcutToTool('C'));
    });
  });

  describe('SHORTCUT_LETTER', () => {
    it('has a letter for every tool in TOOL_SHORTCUT_MAP', () => {
      const tools = new Set(Object.values(TOOL_SHORTCUT_MAP));
      for (const tool of tools) {
        expect(SHORTCUT_LETTER[tool]).toBeDefined();
      }
    });

    it('uses Revu key names', () => {
      for (const letter of Object.values(SHORTCUT_LETTER)) {
        expect(letter).toMatch(/^((Shift|Alt|Ctrl)\+)*[A-Z]$/);
      }
    });
  });

  describe('labelWithShortcut', () => {
    it('appends the letter in parens', () => {
      expect(labelWithShortcut('Length', 'distance')).toBe('Length (Shift+Alt+L)');
      expect(labelWithShortcut('Select', 'select')).toBe('Select (V)');
    });
  });

  describe('shouldHandleShortcut', () => {
    it('returns true for null target', () => {
      expect(shouldHandleShortcut(null)).toBe(true);
    });

    it('returns false for input elements', () => {
      const input = document.createElement('input');
      expect(shouldHandleShortcut(input)).toBe(false);
    });

    it('returns false for textareas', () => {
      const textarea = document.createElement('textarea');
      expect(shouldHandleShortcut(textarea)).toBe(false);
    });

    it('returns false for selects', () => {
      const select = document.createElement('select');
      expect(shouldHandleShortcut(select)).toBe(false);
    });

    it('returns true for non-input elements', () => {
      const div = document.createElement('div');
      expect(shouldHandleShortcut(div)).toBe(true);
    });

    it('returns false for contenteditable', () => {
      const div = document.createElement('div');
      div.setAttribute('contenteditable', 'true');
      // jsdom exposes `isContentEditable` as a getter tied to the attribute.
      Object.defineProperty(div, 'isContentEditable', { value: true });
      expect(shouldHandleShortcut(div)).toBe(false);
    });
  });
});
