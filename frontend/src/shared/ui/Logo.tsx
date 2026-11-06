// DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
// Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
//
// Company branding: the default OpenConstructionERP mark is replaced with
// the Florida Steel Frame & Truss Manufacturing logo (public/brand/company-logo.png).
import clsx from 'clsx';

/** Company display name used wherever the app shows its brand. */
export const COMPANY_NAME = 'Florida Steel Frame & Truss Manufacturing LLC';
/** Company logo (600×150 wordmark, transparent background). */
export const COMPANY_LOGO_URL = '/brand/company-logo.png';
/** Brand colours (from the company colour swatch). */
export const BRAND_MAROON = '#830000';
export const BRAND_GREY = '#616364';

interface LogoProps {
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  animate?: boolean;
  className?: string;
}

/* The logo is a wide (4:1) wordmark, so sizes are driven by height. */
const sizeMap = {
  xs: 'h-5',
  sm: 'h-6',
  md: 'h-10',
  lg: 'h-14',
  xl: 'h-20',
};

/**
 * Company logo. The image has dark lettering on a transparent background,
 * so it sits on a light backing to stay legible in dark mode.
 */
export function Logo({ size = 'md', animate = false, className }: LogoProps) {
  return (
    <div
      className={clsx(
        sizeMap[size],
        'relative shrink-0 inline-flex items-center rounded-md bg-white px-2 py-1 box-content',
        animate && 'animate-fade-in',
        className,
      )}
    >
      <img
        src={COMPANY_LOGO_URL}
        alt={COMPANY_NAME}
        title={COMPANY_NAME}
        className="h-full w-auto object-contain"
        draggable={false}
      />
    </div>
  );
}

/* ── LogoWithText ──────────────────────────────────────────────────────── */

interface LogoWithTextProps extends LogoProps {
  showVersion?: boolean;
}

/* Slightly larger than the bare logo, since the wordmark carries the name. */
const withTextSizeMap = {
  xs: 'sm',
  sm: 'md',
  md: 'lg',
  lg: 'lg',
  xl: 'xl',
} as const;

/** Logo + brand name. The company logo already contains the name. */
export function LogoWithText({ size = 'md', animate, className }: LogoWithTextProps) {
  return (
    <div className={clsx('flex items-center', className)}>
      <Logo size={withTextSizeMap[size]} animate={animate} />
    </div>
  );
}
