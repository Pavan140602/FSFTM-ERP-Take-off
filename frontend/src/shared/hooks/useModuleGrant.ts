// OE-DELIVERY: 2026-10-20-module-grant-hook-v1
// useModuleGrant — shared role-based module visibility check.
//
// Returns whether the current user's role is granted access to a module
// (e.g. 'projects'), matching the sidebar gate: admin always has access,
// and while the grant list is still loading the check fails OPEN (true)
// so nothing flickers away on a slow/failed fetch.
//
// All surfaces that need this check share the ['my-role-modules'] query,
// so the grant list is fetched once for the whole app.

import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '@/stores/useAuthStore';
import { fetchMyRoleModules } from '@/features/users/api';

export function useModuleGrant(moduleKey: string): boolean {
  const userRole = useAuthStore((s) => s.userRole);
  const { data: roleModules } = useQuery({
    queryKey: ['my-role-modules'],
    queryFn: fetchMyRoleModules,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });

  return useMemo(() => {
    if (userRole === 'admin') return true;
    if (!roleModules) return true; // fail-open while loading
    return roleModules.includes(moduleKey);
  }, [userRole, roleModules, moduleKey]);
}
