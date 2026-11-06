// OE-DELIVERY: 2026-10-20-module-route-gate-v1
// ModuleRouteGate — stands in front of a route that belongs to a module.
//
// If the current user's role does not have the module granted (Users →
// Role Module Access), this renders a "No access" empty state instead of
// the page. While the grant list is still loading, the page renders
// (fail-open, matching the sidebar behaviour) so a slow fetch never
// hides a page the user is allowed to see. Admin always has access.

import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { EmptyState } from '@/shared/ui';
import { useModuleGrant } from '@/shared/hooks/useModuleGrant';

export function ModuleRouteGate({
  moduleKey,
  children,
}: {
  moduleKey: string;
  children: ReactNode;
}) {
  const { t } = useTranslation();
  const granted = useModuleGrant(moduleKey);

  if (!granted) {
    return (
      <div className="w-full">
        <EmptyState
          title={t('common.no_access', { defaultValue: 'No access' })}
          description={t('common.no_access_module_desc', {
            defaultValue:
              'Your role does not have access to this module. Ask an admin to enable it in Users → Role Module Access.',
          })}
        />
      </div>
    );
  }
  return <>{children}</>;
}
