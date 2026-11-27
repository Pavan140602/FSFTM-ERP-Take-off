// OE-DELIVERY: 2026-11-27-fsftm-pdf
/**
 * Test page for the PDF Measurements smoke test (scripts/pdf-smoke.cjs).
 *
 * Mounts the real viewer workspace (main drawing + split panes + shared
 * controls) the way TakeoffPage does, with three drawings A, B, C served by
 * the test's mocked API, and exposes a few read-only hooks on `window` so the
 * test can check state. Dev server only - not part of the production build.
 */
import { lazy, Suspense, useState } from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { initialLocaleReady } from '../app/i18n';
import '../index.css';
import { ViewerWorkspace, type WorkspaceDoc } from '../features/takeoff/components/ViewerWorkspace';
import { getShared } from '../modules/pdf-takeoff/data/shared-state';
import { WS_API_KEY, type WorkspaceApi } from '../modules/pdf-takeoff/data/workspace';

const Viewer = lazy(() => import('../modules/pdf-takeoff/TakeoffViewerModule'));
const mk = (n: number, name: string): WorkspaceDoc => {
  const id = `aaaaaaaa-0000-0000-0000-00000000000${n}`;
  return { id, name, url: `/api/v1/takeoff/documents/${id}/download/` };
};
const DOCS = [mk(1, 'Set A.pdf'), mk(2, 'Set B.pdf'), mk(3, 'Set C.pdf')];

function Harness() {
  const [alive, setAlive] = useState<WorkspaceDoc[]>([DOCS[0]!, DOCS[2]!]);
  const [tabs, setTabs] = useState<WorkspaceDoc[]>([DOCS[0]!, DOCS[2]!]);
  const [shown, setShown] = useState(DOCS[0]!.id);
  const open = (d: WorkspaceDoc) => {
    setAlive((p) => (p.some((x) => x.id === d.id) ? p : [...p, d]));
    setTabs((p) => (p.some((x) => x.id === d.id) ? p : [...p, d]));
    setShown(d.id);
  };
  const close = (id: string) => {
    setTabs((p) => p.filter((x) => x.id !== id));
    setAlive((p) => p.filter((x) => x.id !== id));
    if (shown === id) setShown(tabs.find((x) => x.id !== id)?.id ?? DOCS[0]!.id);
  };
  const w = window as unknown as Record<string, unknown>;
  w.__getShared = getShared;
  w.__open = (i: number) => open(DOCS[i]!);
  w.__shown = shown;
  w.__tabs = tabs.map((t) => t.name);
  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }} className="bg-surface-primary">
      <Suspense fallback={null}>
        <ViewerWorkspace
          docs={alive}
          shownId={shown}
          renderViewer={(doc, visible, pane, mirror, key) => (
            <Viewer
              key={key}
              instanceKey={key}
              mirror={mirror}
              hidden={!visible}
              compact={!!pane}
              initialPdfUrl={doc.url}
              initialPdfName={doc.name}
              initialDocumentId={doc.id}
              recentDocuments={DOCS.map((d) => ({ id: d.id, filename: d.name, pages: 1, size_bytes: 1, uploaded_at: null }))}
              openDocuments={tabs.map((d) => ({ id: d.id, name: d.name }))}
              onSwitchDocument={(id) => open(DOCS.find((d) => d.id === id)!)}
              onCloseDocumentTab={close}
              onTabDrop={pane ? (tp) => getShared<WorkspaceApi>(WS_API_KEY)?.dropTabOnPane(tp, pane) : undefined}
            />
          )}
        />
      </Suspense>
    </div>
  );
}

void Promise.resolve(initialLocaleReady).then(() => {
  ReactDOM.createRoot(document.getElementById('root')!).render(
    <QueryClientProvider client={new QueryClient()}>
      <BrowserRouter>
        <Harness />
      </BrowserRouter>
    </QueryClientProvider>,
  );
});
