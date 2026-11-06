// OE-DELIVERY: 2026-11-02-revu-shortcuts
/**
 * Bluebeam Revu default keyboard shortcuts (Revu 20/21, Windows), as listed at
 * support.bluebeam.com/revu/resources/keyboard-shortcuts.html, mapped to the
 * takeoff viewer's tools and actions. Pure so the matcher unit-tests.
 */

export type RevuAction =
  | { kind: 'tool'; tool: string }
  | { kind: 'cmd'; cmd: RevuCommand };

export type RevuCommand =
  | 'pan' | 'zoomTool' | 'zoomIn' | 'zoomOut'
  | 'fitPage' | 'fitWidth' | 'actualSize'
  | 'nextPage' | 'prevPage' | 'firstPage' | 'lastPage'
  | 'splitVertical' | 'splitHorizontal' | 'toggleSplit' | 'unsplit'
  | 'singlePage' | 'continuous' | 'fullScreen'
  | 'panelThumbnails' | 'panelBookmarks' | 'panelMarkups' | 'panelProperties'
  | 'panelToolChest' | 'panelMeasurements' | 'panelLayers' | 'panelSearch'
  | 'find' | 'selectAll' | 'lock' | 'flatten' | 'bringToFront' | 'sendToBack'
  | 'group' | 'ungroup' | 'snapContent' | 'snapMarkup' | 'calibrate';

export interface RevuShortcut {
  keys: string;
  label: string;
  section: 'Markup' | 'Measure' | 'View' | 'Panels' | 'Edit';
  action: RevuAction;
}

const T = (tool: string): RevuAction => ({ kind: 'tool', tool });
const C = (cmd: RevuCommand): RevuAction => ({ kind: 'cmd', cmd });

export const REVU_SHORTCUTS: readonly RevuShortcut[] = [
  // Markup
  { keys: 'V', label: 'Select', section: 'Markup', action: T('select') },
  { keys: 'L', label: 'Line', section: 'Markup', action: T('line') },
  { keys: 'A', label: 'Arrow', section: 'Markup', action: T('arrow') },
  { keys: 'Shift+P', label: 'Polygon', section: 'Markup', action: T('polygon') },
  { keys: 'R', label: 'Rectangle', section: 'Markup', action: T('rectangle') },
  { keys: 'E', label: 'Ellipse', section: 'Markup', action: T('ellipse') },
  { keys: 'C', label: 'Cloud', section: 'Markup', action: T('cloud') },
  { keys: 'K', label: 'Cloud+', section: 'Markup', action: T('cloud') },
  { keys: 'T', label: 'Text Box', section: 'Markup', action: T('text') },
  { keys: 'W', label: 'Typewriter', section: 'Markup', action: T('text') },
  { keys: 'Q', label: 'Callout', section: 'Markup', action: T('callout') },
  { keys: 'N', label: 'Note', section: 'Markup', action: T('callout') },
  { keys: 'H', label: 'Highlight', section: 'Markup', action: T('highlight') },
  { keys: 'P', label: 'Pen', section: 'Markup', action: T('pen') },
  { keys: 'S', label: 'Stamp', section: 'Markup', action: T('stamp') },
  { keys: 'Shift+L', label: 'Dimension', section: 'Markup', action: T('distance') },
  { keys: 'Shift+C', label: 'Arc', section: 'Markup', action: T('arc') },
  // Measure
  { keys: 'Shift+Alt+L', label: 'Length', section: 'Measure', action: T('distance') },
  { keys: 'Shift+Alt+Q', label: 'Polylength', section: 'Measure', action: T('polyline') },
  { keys: 'Shift+Alt+A', label: 'Area', section: 'Measure', action: T('area') },
  { keys: 'Shift+Alt+P', label: 'Perimeter', section: 'Measure', action: T('perimeter') },
  { keys: 'Shift+Alt+V', label: 'Volume', section: 'Measure', action: T('volume') },
  { keys: 'Shift+Alt+C', label: 'Count', section: 'Measure', action: T('count') },
  { keys: 'Shift+Alt+D', label: 'Diameter', section: 'Measure', action: T('diameter') },
  { keys: 'Shift+Alt+G', label: 'Angle', section: 'Measure', action: T('angle') },
  { keys: 'Shift+Alt+U', label: 'Radius', section: 'Measure', action: T('radiusCenter') },
  { keys: 'J', label: 'Dynamic Fill', section: 'Measure', action: T('dynamicFill') },
  // View
  { keys: 'Shift+V', label: 'Pan', section: 'View', action: C('pan') },
  { keys: 'Z', label: 'Zoom tool', section: 'View', action: C('zoomTool') },
  { keys: '+', label: 'Zoom in', section: 'View', action: C('zoomIn') },
  { keys: '-', label: 'Zoom out', section: 'View', action: C('zoomOut') },
  { keys: 'Ctrl+9', label: 'Fit page', section: 'View', action: C('fitPage') },
  { keys: 'Ctrl+0', label: 'Fit width', section: 'View', action: C('fitWidth') },
  { keys: 'Ctrl+8', label: 'Actual size', section: 'View', action: C('actualSize') },
  { keys: 'Ctrl+Right', label: 'Next page', section: 'View', action: C('nextPage') },
  { keys: 'Ctrl+Left', label: 'Previous page', section: 'View', action: C('prevPage') },
  { keys: 'Home', label: 'First page', section: 'View', action: C('firstPage') },
  { keys: 'End', label: 'Last page', section: 'View', action: C('lastPage') },
  { keys: 'Ctrl+2', label: 'Split vertical', section: 'View', action: C('splitVertical') },
  { keys: 'Ctrl+H', label: 'Split horizontal', section: 'View', action: C('splitHorizontal') },
  { keys: 'Ctrl+I', label: 'Toggle split', section: 'View', action: C('toggleSplit') },
  { keys: 'Ctrl+Shift+2', label: 'Unsplit', section: 'View', action: C('unsplit') },
  { keys: 'Ctrl+4', label: 'Single page', section: 'View', action: C('singlePage') },
  { keys: 'Ctrl+5', label: 'Continuous', section: 'View', action: C('continuous') },
  { keys: 'F11', label: 'Full screen', section: 'View', action: C('fullScreen') },
  // Panels
  { keys: 'Alt+T', label: 'Thumbnails', section: 'Panels', action: C('panelThumbnails') },
  { keys: 'Alt+B', label: 'Bookmarks (page index)', section: 'Panels', action: C('panelBookmarks') },
  { keys: 'Alt+L', label: 'Markups list', section: 'Panels', action: C('panelMarkups') },
  { keys: 'Alt+X', label: 'Tool Chest', section: 'Panels', action: C('panelToolChest') },
  { keys: 'Alt+U', label: 'Measurements', section: 'Panels', action: C('panelMeasurements') },
  { keys: 'Alt+1', label: 'Search', section: 'Panels', action: C('panelSearch') },
  // Edit
  { keys: 'Ctrl+F', label: 'Find', section: 'Edit', action: C('find') },
  { keys: 'Ctrl+A', label: 'Select all', section: 'Edit', action: C('selectAll') },
  { keys: 'Ctrl+Shift+L', label: 'Lock / unlock', section: 'Edit', action: C('lock') },
  { keys: 'Ctrl+Shift+M', label: 'Flatten', section: 'Edit', action: C('flatten') },
  { keys: 'Ctrl+Shift+J', label: 'Bring to front', section: 'Edit', action: C('bringToFront') },
  { keys: 'Ctrl+Shift+[', label: 'Send to back', section: 'Edit', action: C('sendToBack') },
  { keys: 'Ctrl+G', label: 'Group', section: 'Edit', action: C('group') },
  { keys: 'Ctrl+Shift+G', label: 'Ungroup', section: 'Edit', action: C('ungroup') },
  { keys: 'Ctrl+Shift+F8', label: 'Snap to content', section: 'Edit', action: C('snapContent') },
  { keys: 'Ctrl+Shift+F7', label: 'Snap to markup', section: 'Edit', action: C('snapMarkup') },
];

/** Shortcuts the viewer already handles itself (listed for the help sheet). */
export const REVU_EXTRA_HELP: readonly { keys: string; label: string }[] = [
  { keys: 'Ctrl+Z / Ctrl+Y', label: 'Undo / redo' },
  { keys: 'Ctrl+D', label: 'Duplicate' },
  { keys: 'Delete', label: 'Delete markup or vertex' },
  { keys: 'Arrows (Shift ×10)', label: 'Nudge markup' },
  { keys: '[ / ]', label: 'Shorten / lengthen a line' },
  { keys: 'Space (hold)', label: 'Pan while drawing' },
  { keys: 'Esc', label: 'Cancel / back to Select' },
  { keys: 'Enter / double-click', label: 'Finish a shape' },
];

interface KeyLike {
  key: string;
  code?: string;
  ctrlKey: boolean;
  metaKey?: boolean;
  shiftKey: boolean;
  altKey: boolean;
}

/** The canonical "Ctrl+Shift+Alt+X" string for a key event. */
export function comboOf(e: KeyLike): string {
  let k: string;
  const code = e.code ?? '';
  if (/^Key[A-Z]$/.test(code)) k = code.slice(3);
  else if (/^Digit[0-9]$/.test(code)) k = code.slice(5);
  else if (/^Numpad[0-9]$/.test(code)) k = code.slice(6);
  else if (code === 'BracketLeft') k = '[';
  else if (code === 'BracketRight') k = ']';
  else if (code === 'NumpadAdd' || e.key === '+' || (code === 'Equal' && e.shiftKey)) k = '+';
  else if (code === 'NumpadSubtract' || code === 'Minus' || e.key === '-') k = '-';
  else if (e.key === 'ArrowRight') k = 'Right';
  else if (e.key === 'ArrowLeft') k = 'Left';
  else if (e.key.length === 1) k = e.key.toUpperCase();
  else k = e.key;
  const parts: string[] = [];
  if (e.ctrlKey || e.metaKey) parts.push('Ctrl');
  // '+' is typed with Shift on most layouts; it is listed without it.
  if (e.shiftKey && k !== '+') parts.push('Shift');
  if (e.altKey) parts.push('Alt');
  parts.push(k);
  return parts.join('+');
}

const BY_COMBO = new Map(REVU_SHORTCUTS.map((s) => [s.keys, s]));

/** The Revu shortcut a key event triggers, or null. */
export function matchRevuShortcut(e: KeyLike): RevuShortcut | null {
  return BY_COMBO.get(comboOf(e)) ?? null;
}

/** Revu key for a tool, for tooltips ("Length (Shift+Alt+L)"). Measure keys
 *  win over the markup alias where a tool has both. */
export function revuKeyForTool(tool: string): string | undefined {
  const hits = REVU_SHORTCUTS.filter((s) => s.action.kind === 'tool' && s.action.tool === tool);
  const measure = hits.find((s) => s.section === 'Measure');
  return (measure ?? hits[0])?.keys;
}
