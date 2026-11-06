// DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
// Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
import { useToastStore } from '@/stores/useToastStore';
import { isTauri } from '@/shared/lib/desktop';
import { Toast } from './Toast';

const TOAST_TOP = `calc(var(--oe-header-height, 52px) + ${isTauri ? '36px' : '0px'} + 0.75rem)`;

export function ToastContainer() {
  const toasts = useToastStore((s) => s.toasts);
  const removeToast = useToastStore((s) => s.removeToast);
  const topToasts = toasts.filter((t) => t.placement !== 'bottom');

  if (topToasts.length === 0) return null;

  return (
    // Toasts start below the top bar (and below the desktop shell's toolbar)
    // so they never cover its buttons or what the reader was about to click.
    <div
      className="oe-dock-aware fixed right-4 z-[9999] flex flex-col gap-2"
      style={{ top: TOAST_TOP }}
      data-testid="toast-stack"
    >
      {topToasts.map((toast) => (
        <Toast key={toast.id} toast={toast} onDismiss={removeToast} />
      ))}
    </div>
  );
}

/** Bottom-right toast stack — used for incoming-notification popups. */
export function NotificationToastContainer() {
  const toasts = useToastStore((s) => s.toasts);
  const removeToast = useToastStore((s) => s.removeToast);
  const bottomToasts = toasts.filter((t) => t.placement === 'bottom');

  if (bottomToasts.length === 0) return null;

  return (
    <div
      className="oe-dock-aware fixed bottom-4 right-4 z-[9999] flex flex-col gap-2"
      data-testid="notification-toast-stack"
    >
      {bottomToasts.map((toast) => (
        <Toast key={toast.id} toast={toast} onDismiss={removeToast} />
      ))}
    </div>
  );
}
