"""Update 15b: Save button + Ctrl+S (saves the work now), Close PDF button
and File > Close (OE-DELIVERY 2026-11-12-revu-ui)."""
from pathlib import Path

base = Path(r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\frontend\src")
p = base / "modules/pdf-takeoff/TakeoffViewerModule.tsx"
s = p.read_text(encoding="utf-8")


def rep(a, b, n=1):
    global s
    c = s.count(a)
    assert c == n, (c, a[:100])
    s = s.replace(a, b)


rep("""  /** Open one of the recent documents in the viewer (parent owns navigation). */
  onOpenRecentDocument?: (docId: string) => void;
}""", """  /** Open one of the recent documents in the viewer (parent owns navigation). */
  onOpenRecentDocument?: (docId: string) => void;
  /** Close the open PDF (parent clears it; the viewer saves first, update 15). */
  onCloseDocument?: () => void;
}""")
# Destructure the prop: find the component signature.
i = s.index("onOpenRecentDocument,", s.index("export function TakeoffViewerModule") if "export function TakeoffViewerModule" in s else s.index("function TakeoffViewerModule"))
s = s[:i] + "onOpenRecentDocument,\n  onCloseDocument," + s[i + len("onOpenRecentDocument,"):]

# Save handler (shared by button, menu and Ctrl+S).
rep("""  const { hasPersistedData, saveNow, clearPersisted, syncing, syncedToServer, registerDeletion, hasUnsavedChanges } = useMeasurementPersistence({""",
    """  const { hasPersistedData, saveNow, clearPersisted, syncing, syncedToServer, registerDeletion, hasUnsavedChanges } = useMeasurementPersistence({""")
anchor = "  /* ── Load PDF ────────────────────────────────────────────────────── */"
assert s.count(anchor) == 1
s = s.replace(anchor, """  /** Save the work now (button, File > Save, Ctrl+S - update 15). */
  const saveWorkRef = useRef<() => void>(() => {});
  saveWorkRef.current = () => {
    try { saveNow(); } catch { /* the debounced sync still runs */ }
    addToast({ type: 'success', title: 'Saved', message: documentId ? 'Markups and scales saved to the project.' : 'Saved on this computer (local file).' });
  };
  /** Close the PDF: save, then hand back to the document list. */
  const closePdf = () => {
    try { saveNow(); } catch { /* teardown flush saves too */ }
    onCloseDocument?.();
  };

""" + anchor)
rep("""                { label: 'Save', shortcut: 'Ctrl+S', onClick: () => { void saveNow(); } },""",
    """                { label: 'Save', shortcut: 'Ctrl+S', onClick: () => saveWorkRef.current(), testId: 'revu-file-save' },
                ...(onCloseDocument ? [{ label: 'Close PDF', onClick: () => closePdf(), testId: 'revu-file-close' }] : []),""")
# Ctrl+S.
rep("""      // Undo / Redo — handled even inside inputs (standard browser semantics).""",
    """      // Ctrl+S saves the work (update 15).
      if ((e.ctrlKey || e.metaKey) && !e.shiftKey && e.key.toLowerCase() === 's') {
        e.preventDefault();
        saveWorkRef.current();
        return;
      }

      // Undo / Redo — handled even inside inputs (standard browser semantics).""")
# Toolbar: Save + Close PDF.
rep("""                {/* Save PDF - the document's hero action. */}
                <button""", """                {/* Save the work (update 15). */}
                <button
                  onClick={() => saveWorkRef.current()}
                  disabled={!pdfDoc}
                  className="inline-flex h-7 items-center gap-1.5 rounded-md border border-oe-blue/40 bg-surface-primary px-2.5 text-xs font-semibold text-oe-blue transition-colors hover:bg-oe-blue/10 disabled:opacity-50"
                  title="Save your work now (Ctrl+S). Markups and scales also save automatically."
                  data-testid="toolbar-save-button"
                >
                  {syncing ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                  <span className="takeoff-toolbar-label">Save</span>
                </button>
                {onCloseDocument && (
                  <button
                    onClick={closePdf}
                    disabled={!pdfDoc}
                    className="inline-flex h-7 items-center gap-1 rounded-md border border-border bg-surface-primary px-2 text-xs font-medium text-content-secondary transition-colors hover:border-red-300 hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
                    title="Close this PDF (your work is saved first)"
                    data-testid="toolbar-close-pdf"
                  >
                    <X size={14} />
                    <span className="takeoff-toolbar-label">Close PDF</span>
                  </button>
                )}
                {/* Save PDF - the document's hero action. */}
                <button""")
p.write_text(s, encoding="utf-8")

# Parent: close = clear the open document and the URL.
q = base / "features/takeoff/TakeoffPage.tsx"
t = q.read_text(encoding="utf-8")
a = """                  recentDocuments={serverDocuments}
                  onOpenRecentDocument={handleOpenDocInViewer}
                />"""
assert t.count(a) == 1
t = t.replace(a, """                  recentDocuments={serverDocuments}
                  onOpenRecentDocument={handleOpenDocInViewer}
                  onCloseDocument={() => {
                    // Close PDF (update 15): back to the drawing list.
                    setViewerDoc(null);
                    setActiveDocId(null);
                    setSearchParams(
                      (prev) => {
                        const next = new URLSearchParams(prev);
                        next.delete('doc');
                        next.delete('page');
                        return next;
                      },
                      { replace: true },
                    );
                  }}
                />""")
q.write_text(t, encoding="utf-8")
print("ok")
