// OE-DELIVERY: 2026-10-08-manage-columns-safe
/**
 * Bluebeam-style "Manage Columns" dialog for the Markups List.
 *
 * Two tabs:
 *  - Display Order: checkbox list of built-in columns with show/hide toggles.
 *  - Custom Columns: add / delete custom columns, plus Import / Export (JSON).
 *
 * Safe implementation: visibility is applied via CSS display:none in the
 * ledger (no JSX structure changes), so it cannot break rendering.
 */
import { useState } from 'react';
import { X, Plus, Trash2, Upload, Download } from 'lucide-react';

export interface ManageColumnsDialogProps {
  /** Built-in columns with visibility. */
  builtInColumns: { key: string; label: string; visible: boolean }[];
  /** Custom column names. */
  customColumns: string[];
  onBuiltInChange: (cols: { key: string; label: string; visible: boolean }[]) => void;
  onCustomChange: (cols: string[]) => void;
  onClose: () => void;
}

export function ManageColumnsDialog({
  builtInColumns,
  customColumns,
  onBuiltInChange,
  onCustomChange,
  onClose,
}: ManageColumnsDialogProps) {
  const [tab, setTab] = useState<'display' | 'custom'>('display');
  const [newColName, setNewColName] = useState('');

  const toggleBuiltIn = (key: string) => {
    onBuiltInChange(
      builtInColumns.map((c) => (c.key === key ? { ...c, visible: !c.visible } : c)),
    );
  };

  const addCustom = () => {
    const name = newColName.trim();
    if (!name) return;
    if (customColumns.some((c) => c.toLowerCase() === name.toLowerCase())) return;
    onCustomChange([...customColumns, name]);
    setNewColName('');
  };

  const deleteCustom = (name: string) => {
    onCustomChange(customColumns.filter((c) => c !== name));
  };

  const handleImport = (file: File) => {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const parsed = JSON.parse(String(reader.result));
        if (Array.isArray(parsed)) {
          const cols = parsed
            .map((p) => (typeof p === 'string' ? p : p?.name))
            .filter((n): n is string => typeof n === 'string' && n.trim().length > 0);
          onCustomChange([...new Set([...customColumns, ...cols])]);
        }
      } catch {
        /* ignore malformed file */
      }
    };
    reader.readAsText(file);
  };

  const handleExport = () => {
    const blob = new Blob([JSON.stringify(customColumns, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'markups-custom-columns.json';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div
      className="fixed inset-0 z-[80] flex items-center justify-center bg-black/60 p-4"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      role="dialog"
      aria-modal="true"
      aria-label="Manage Columns"
    >
      <div className="w-full max-w-md rounded-xl border border-border bg-surface-primary shadow-2xl">
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <h3 className="text-sm font-semibold text-content-primary">Manage Columns</h3>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-content-tertiary hover:bg-surface-secondary hover:text-content-primary"
            aria-label="Close"
          >
            <X size={16} />
          </button>
        </div>

        <div className="flex gap-1 border-b border-border px-4 pt-2">
          <button
            type="button"
            onClick={() => setTab('display')}
            className={`rounded-t-md px-4 py-2 text-xs font-semibold transition-colors ${
              tab === 'display'
                ? 'bg-oe-blue text-white'
                : 'text-content-secondary hover:bg-surface-secondary'
            }`}
          >
            Display Order
          </button>
          <button
            type="button"
            onClick={() => setTab('custom')}
            className={`rounded-t-md px-4 py-2 text-xs font-semibold transition-colors ${
              tab === 'custom'
                ? 'bg-oe-blue text-white'
                : 'text-content-secondary hover:bg-surface-secondary'
            }`}
          >
            Custom Columns
          </button>
        </div>

        <div className="p-4">
          {tab === 'display' && (
            <div>
              <p className="mb-2 text-[11px] font-semibold uppercase tracking-widest text-content-tertiary">
                Column Display Order
              </p>
              <div className="max-h-64 overflow-y-auto rounded-md border border-border">
                {builtInColumns.map((col) => (
                  <label
                    key={col.key}
                    className="flex cursor-pointer items-center gap-2 border-b border-border/50 px-3 py-2 text-xs hover:bg-surface-secondary/50 last:border-0"
                  >
                    <input
                      type="checkbox"
                      checked={col.visible}
                      onChange={() => toggleBuiltIn(col.key)}
                      className="h-3.5 w-3.5 accent-oe-blue"
                    />
                    <span className="flex-1 text-content-primary">{col.label}</span>
                    <span className="text-[10px] text-content-tertiary">Built-in</span>
                  </label>
                ))}
              </div>
              <button
                type="button"
                onClick={() =>
                  onBuiltInChange(builtInColumns.map((c) => ({ ...c, visible: true })))
                }
                className="mt-2 rounded-md border border-border px-3 py-1.5 text-xs text-content-secondary hover:bg-surface-secondary"
              >
                Reset
              </button>
            </div>
          )}

          {tab === 'custom' && (
            <div>
              <p className="mb-2 text-[11px] font-semibold uppercase tracking-widest text-content-tertiary">
                Custom Columns
              </p>
              <div className="max-h-48 overflow-y-auto rounded-md border border-border">
                {customColumns.map((name) => (
                  <div
                    key={name}
                    className="flex items-center justify-between border-b border-border/50 px-3 py-2 text-xs last:border-0"
                  >
                    <span className="text-content-primary">{name}</span>
                    <button
                      type="button"
                      onClick={() => deleteCustom(name)}
                      className="rounded p-1 text-content-tertiary hover:bg-surface-secondary hover:text-red-500"
                      title={`Delete ${name}`}
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                ))}
                {customColumns.length === 0 && (
                  <p className="px-3 py-4 text-center text-xs text-content-tertiary">
                    No custom columns yet.
                  </p>
                )}
              </div>
              <div className="mt-3 flex gap-2">
                <input
                  type="text"
                  value={newColName}
                  onChange={(e) => setNewColName(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') addCustom();
                  }}
                  placeholder="New column name"
                  className="flex-1 rounded-md border border-border bg-surface-secondary px-2 py-1.5 text-xs text-content-primary"
                />
                <button
                  type="button"
                  onClick={addCustom}
                  className="flex items-center gap-1 rounded-md bg-oe-blue px-3 py-1.5 text-xs font-semibold text-white hover:opacity-90"
                >
                  <Plus size={12} />
                  Add
                </button>
              </div>
              <div className="mt-3 flex gap-2">
                <label className="flex cursor-pointer items-center gap-1 rounded-md border border-border px-3 py-1.5 text-xs text-content-secondary hover:bg-surface-secondary">
                  <Upload size={12} />
                  Import
                  <input
                    type="file"
                    accept=".json"
                    className="hidden"
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      if (f) handleImport(f);
                      e.target.value = '';
                    }}
                  />
                </label>
                <button
                  type="button"
                  onClick={handleExport}
                  className="flex items-center gap-1 rounded-md border border-border px-3 py-1.5 text-xs text-content-secondary hover:bg-surface-secondary"
                >
                  <Download size={12} />
                  Export
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2 border-t border-border px-4 py-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded-md bg-oe-blue px-4 py-1.5 text-xs font-semibold text-white hover:opacity-90"
          >
            OK
          </button>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-border px-4 py-1.5 text-xs text-content-secondary hover:bg-surface-secondary"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
