// DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
import { useToastStore } from '../../../stores/useToastStore';
import { Toast } from '@/shared/ui/Toast';

/** Toast stack rendered INSIDE the fullscreen viewer element. The global
 *  ToastContainer lives at document level, which the browser hides while an
 *  element is fullscreen — without this, no notification is visible in
 *  fullscreen measuring mode. */
export function FullscreenToastStack() {
  const toasts = useToastStore((s) => s.toasts);
  const removeToast = useToastStore((s) => s.removeToast);
  if (toasts.length === 0) return null;
  return (
    <div
      className="fixed right-4 top-4 z-[9999] flex flex-col gap-2"
      data-testid="toast-stack-fullscreen"
    >
      {toasts.map((toast) => (
        <Toast key={toast.id} toast={toast} onDismiss={removeToast} />
      ))}
    </div>
  );
}
