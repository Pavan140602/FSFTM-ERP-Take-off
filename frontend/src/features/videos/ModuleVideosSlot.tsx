// DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
// Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
//
// Mounted once in the app shell. On a screen the catalogue links videos to,
// and unless the reader hid the hint, it loads the "Videos for this step"
// panel; everywhere else it renders nothing and loads nothing.

import { lazy, Suspense, useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { useVideoHintsStore, videoRouteFor } from './videoRoutes';

const ModuleVideosPanel = lazy(() => import('./ModuleVideosPanel'));

/** PDF Measurements in compact mode hides this bar so the drawing gets the
 *  room (OE-DELIVERY 2026-11-04-takeoff-workarea). */
function useTakeoffCompact(pathname: string): boolean {
  const read = () => {
    try { return pathname.startsWith('/takeoff') && localStorage.getItem('takeoff.compactHeader') !== '0'; } catch { return false; }
  };
  const [on, setOn] = useState(read);
  useEffect(() => {
    setOn(read());
    const h = () => setOn(read());
    window.addEventListener('takeoff-compact-change', h);
    return () => window.removeEventListener('takeoff-compact-change', h);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname]);
  return on;
}

export function ModuleVideosSlot() {
  const { pathname } = useLocation();
  const route = videoRouteFor(pathname);
  const hidden = useVideoHintsStore((s) => (route ? s.off || s.hidden.includes(route) : true));
  const compactTakeoff = useTakeoffCompact(pathname);
  if (!route || hidden || compactTakeoff) return null;
  return (
    <Suspense fallback={null}>
      <ModuleVideosPanel key={route} route={route} />
    </Suspense>
  );
}
