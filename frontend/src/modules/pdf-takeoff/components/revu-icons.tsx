// OE-DELIVERY: 2026-11-12-revu-ui
/**
 * Tool icons drawn in the style of Bluebeam Revu's toolbars (original
 * artwork, not Bluebeam's): measure tools as small line diagrams with
 * dimension ticks and a blue accent, markup tools in red / orange, the way
 * Revu colours its markup set. Same props as a lucide icon (size,
 * className), so they drop into the tool strip, menus and Tool Chest.
 */
import type { ComponentType, ReactNode } from 'react';

export type ToolIcon = ComponentType<{ size?: number | string; className?: string; strokeWidth?: number | string }>;

const BLUE = '#1E6FD9';
const RED = '#E0301E';
const ORANGE = '#F08A00';
const FILL_BLUE = 'rgba(30,111,217,0.22)';
const FILL_RED = 'rgba(224,48,30,0.15)';
const YELLOW = 'rgba(255,214,0,0.75)';

function make(name: string, body: ReactNode): ToolIcon {
  const Icon = ({ size = 16, className }: { size?: number | string; className?: string }) => (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.6}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
      data-revu-icon={name}
    >
      {body}
    </svg>
  );
  Icon.displayName = `RevuIcon(${name})`;
  return Icon;
}

/** Dimension end ticks at (x, y), perpendicular to a horizontal line. */
const tick = (x: number, y: number) => <path d={`M${x} ${y - 3}v6`} stroke={BLUE} />;

export const RevuSelect = make('select', (
  <path d="M5 3l12 9-5.2 1 3.4 6.5-2.3 1.2-3.3-6.5L5 18z" fill="currentColor" fillOpacity={0.12} />
));
export const RevuLength = make('length', (
  <>
    <path d="M3 12h18" />
    {tick(3, 12)}
    {tick(21, 12)}
    <path d="M9 8h6" stroke={BLUE} strokeWidth={1.2} />
  </>
));
export const RevuPolylength = make('polylength', (
  <>
    {/* Revu Polylength (update 11): a polyline with square grips at its
        vertices, in violet corner brackets. */}
    <path d="M3 7V3h4M17 3h4v4M21 17v4h-4M7 21H3v-4" stroke="#7C5CFF" strokeWidth={1.4} />
    <path d="M7 17V9l5-3 5 4" strokeWidth={1.5} />
    <rect x="5.6" y="15.6" width="2.8" height="2.8" fill="currentColor" stroke="none" />
    <rect x="5.6" y="7.6" width="2.8" height="2.8" fill="currentColor" stroke="none" />
    <rect x="10.6" y="4.6" width="2.8" height="2.8" fill="currentColor" stroke="none" />
    <rect x="15.6" y="8.6" width="2.8" height="2.8" fill="currentColor" stroke="none" />
  </>
));
export const RevuArea = make('area', (
  <path d="M4 7l7-4 9 5-2 11H6z" fill={FILL_BLUE} stroke={BLUE} />
));
export const RevuRectArea = make('rectarea', (
  <rect x="3.5" y="6" width="17" height="12" fill={FILL_BLUE} stroke={BLUE} />
));
export const RevuPerimeter = make('perimeter', (
  <>
    <path d="M4 7l7-4 9 5-2 11H6z" />
    <path d="M4 7l7-4" stroke={BLUE} strokeWidth={2.2} />
  </>
));
export const RevuVolume = make('volume', (
  <>
    <path d="M4 8l8-4 8 4v9l-8 4-8-4z" fill={FILL_BLUE} />
    <path d="M4 8l8 4 8-4M12 12v9" />
  </>
));
export const RevuCount = make('count', (
  <>
    <circle cx="7" cy="8" r="2.4" fill={BLUE} stroke="none" />
    <circle cx="17" cy="8" r="2.4" fill={BLUE} stroke="none" />
    <circle cx="7" cy="17" r="2.4" fill={BLUE} stroke="none" />
    <path d="M14 17l2 2 4-4" stroke={RED} strokeWidth={2} />
  </>
));
export const RevuDiameter = make('diameter', (
  <>
    <circle cx="12" cy="12" r="8" />
    <path d="M6.3 17.7L17.7 6.3" stroke={BLUE} />
  </>
));
export const RevuRadius = make('radius', (
  <>
    <circle cx="12" cy="12" r="8" />
    <path d="M12 12l6.5-4.5" stroke={BLUE} />
    <circle cx="12" cy="12" r="1.2" fill="currentColor" stroke="none" />
  </>
));
export const RevuRadius3 = make('radius3', (
  <>
    <path d="M4 17a9 9 0 0 1 16 0" />
    <circle cx="4" cy="17" r="1.5" fill={BLUE} stroke="none" />
    <circle cx="12" cy="8.5" r="1.5" fill={BLUE} stroke="none" />
    <circle cx="20" cy="17" r="1.5" fill={BLUE} stroke="none" />
  </>
));
export const RevuAngle = make('angle', (
  <>
    <path d="M4 19h16M4 19L15 5" />
    <path d="M10 19a6 6 0 0 0-2.3-4.7" stroke={BLUE} />
  </>
));
export const RevuArc = make('arc', (
  <>
    <path d="M4 18c2-9 14-9 16 0" />
    {tick(4, 18)}
    {tick(20, 18)}
  </>
));
export const RevuPolyCutout = make('polycutout', (
  <>
    <rect x="3" y="4" width="18" height="16" fill={FILL_BLUE} stroke={BLUE} />
    <path d="M9 9l6-1 1 6-6 1z" fill="#fff" stroke="currentColor" strokeDasharray="2 1.5" />
  </>
));
export const RevuEllipseCutout = make('ellipsecutout', (
  <>
    <rect x="3" y="4" width="18" height="16" fill={FILL_BLUE} stroke={BLUE} />
    <ellipse cx="12" cy="12" rx="4.5" ry="3.5" fill="#fff" stroke="currentColor" strokeDasharray="2 1.5" />
  </>
));
export const RevuDynamicFill = make('dynamicfill', (
  <>
    <path d="M5 11l6-6 7 7-6 6z" fill={FILL_BLUE} />
    <path d="M18 14c1.2 1.7 2 2.9 2 3.8a2 2 0 0 1-4 0c0-.9.8-2.1 2-3.8z" fill={BLUE} stroke="none" />
  </>
));
export const RevuLine = make('line', <path d="M4 19L20 5" stroke={RED} strokeWidth={2} />);
export const RevuArrow = make('arrow', (
  <>
    <path d="M4 20L19 5" stroke={RED} strokeWidth={2} />
    <path d="M11 5h8v8" stroke={RED} strokeWidth={2} />
  </>
));
export const RevuTextBox = make('text', (
  <>
    <rect x="3" y="4" width="18" height="16" stroke={RED} />
    <path d="M8 9h8M12 9v7" strokeWidth={2} />
  </>
));
export const RevuCallout = make('callout', (
  <>
    <rect x="9" y="3.5" width="12" height="9" stroke={RED} />
    <path d="M9 10L3 20" stroke={RED} strokeWidth={1.8} />
    <path d="M12 7h6M12 9.5h4" strokeWidth={1.2} />
  </>
));
export const RevuCloud = make('cloud', (
  <path
    d="M5 9a2.3 2.3 0 0 1 4-1.8 2.6 2.6 0 0 1 5 0 2.3 2.3 0 0 1 4 1.6 2.3 2.3 0 0 1 1 4.3 2.3 2.3 0 0 1-3 2.7 2.6 2.6 0 0 1-5 .6 2.4 2.4 0 0 1-4.5-.8A2.3 2.3 0 0 1 4.5 13 2.3 2.3 0 0 1 5 9z"
    fill={FILL_RED}
    stroke={RED}
    strokeWidth={1.7}
  />
));
export const RevuRectangle = make('rectangle', <rect x="3.5" y="6" width="17" height="12" stroke={RED} strokeWidth={1.9} />);
export const RevuEllipse = make('ellipse', <ellipse cx="12" cy="12" rx="8.5" ry="6" stroke={RED} strokeWidth={1.9} />);
export const RevuPolygon = make('polygon', <path d="M12 3l8 6-3 10H7L4 9z" stroke={RED} strokeWidth={1.9} />);
export const RevuPen = make('pen', (
  <>
    <path d="M4 17c3-1 4-6 7-6s2 5 5 5 3-3 4-4" stroke={RED} strokeWidth={1.9} />
    <path d="M15 3l3 3-7 7H8v-3z" strokeWidth={1.3} />
  </>
));
export const RevuHighlight = make('highlight', (
  <>
    <rect x="3" y="12" width="18" height="6" fill={YELLOW} stroke="none" />
    <path d="M9 13l6-9 3 2-6 9z" strokeWidth={1.4} />
  </>
));
export const RevuStamp = make('stamp', (
  <>
    <rect x="4" y="13" width="16" height="5" stroke={ORANGE} strokeWidth={1.8} />
    <path d="M9 13V9a3 3 0 1 1 6 0v4" />
    <path d="M6 21h12" />
  </>
));

export const RevuPolylineMarkup = make('polylinemarkup', <path d="M3 18l6-9 5 6 7-10" stroke={RED} strokeWidth={1.9} />);

export const RevuCloudPlus = make('cloudplus', (
  <>
    <path d="M3 11a2 2 0 0 1 3.4-1.5 2.2 2.2 0 0 1 4.2 0 2 2 0 0 1 3.4 1.4 2 2 0 0 1-.4 3.6 2.2 2.2 0 0 1-4.2.5A2 2 0 0 1 6 15.6 2 2 0 0 1 3 11z" fill={FILL_RED} stroke={RED} strokeWidth={1.5} />
    <path d="M13.5 9.5L17 6" stroke={RED} strokeWidth={1.3} />
    <rect x="16.5" y="2.5" width="5" height="4.5" stroke={RED} strokeWidth={1.3} />
  </>
));
