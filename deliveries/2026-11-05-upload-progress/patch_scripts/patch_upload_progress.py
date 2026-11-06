# OE-DELIVERY 2026-11-05-upload-progress: progress bar (percent, MB, time left) for uploads.
from pathlib import Path
import sys

P = Path(sys.argv[1]) / "frontend/src/features/takeoff/TakeoffPage.tsx"
s = P.read_text(encoding="utf-8")


def rep(old, new):
    global s
    if s.count(old) != 1:
        print("ANCHOR FAIL", s.count(old), old[:140])
        sys.exit(1)
    s = s.replace(old, new)


rep('''  uploading?: boolean;
}
''', '''  uploading?: boolean;
  /** Bytes sent so far (OE-DELIVERY 2026-11-05-upload-progress). */
  uploadProgress?: UploadProgress;
}
''')

rep('''interface UploadedDocument {''', '''import { xhrUpload, type UploadProgress } from './lib/upload-progress';
import { UploadProgressBar } from './components/UploadProgressBar';

interface UploadedDocument {''')

# Documents tab card
rep('''          <p className="mt-0.5 text-xs text-content-tertiary">
            {doc.pages > 0 ? `${doc.pages} ${t('takeoff.pages', 'pages')} \\u2022 ` : ''}''', '''          {isUploading && <UploadProgressBar progress={doc.uploadProgress} />}
          <p className="mt-0.5 text-xs text-content-tertiary">
            {doc.pages > 0 ? `${doc.pages} ${t('takeoff.pages', 'pages')} \\u2022 ` : ''}''')

# filmstrip card
rep('''                      <span>{formatFileSize(doc.size_bytes)}</span>
                      {doc.uploaded_at && (
                        <>
                          <span>&middot;</span>
                          <span>{formatTimeAgo(doc.uploaded_at, t)}</span>
                        </>
                      )}
                    </div>
                  </div>''', '''                      <span>{formatFileSize(doc.size_bytes)}</span>
                      {doc.uploaded_at && (
                        <>
                          <span>&middot;</span>
                          <span>{formatTimeAgo(doc.uploaded_at, t)}</span>
                        </>
                      )}
                    </div>
                    {isUploading && <UploadProgressBar progress={doc.uploadProgress} compact />}
                  </div>''')

# mutation: XHR with progress
rep('''  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append('file', file);

      const token = useAuthStore.getState().accessToken;
      const headers: HeadersInit = {};''', '''  const uploadMutation = useMutation({
    mutationFn: async ({ file, onProgress }: { file: File; onProgress?: (loaded: number, total: number) => void }) => {
      const formData = new FormData();
      formData.append('file', file);

      const token = useAuthStore.getState().accessToken;
      const headers: Record<string, string> = {};''')
start = s.index("      const response = await fetch(uploadUrl, {\n        method: 'POST',")
end = s.index("    // NOTE: onSuccess/onError handled per-call in handleFilesSelected")
s = s[:start] + '''      // XMLHttpRequest instead of fetch: it reports bytes sent, which drives
      // the progress bar. Error replies still surface the server's
      // {"detail": "..."} message (D-TKC-UP01).
      return xhrUpload<{
        id: string;
        filename: string;
        pages: number;
        size_bytes: number;
      }>(uploadUrl, formData, headers, onProgress);
    },
''' + s[end:]

rep('''        setDocuments((prev) => [...prev, localDoc]);

        // Attempt to upload; on success replace the temp entry
        uploadMutation.mutate(file, {''', '''        setDocuments((prev) => [...prev, { ...localDoc, uploadProgress: { loaded: 0, total: file.size, startedAt: Date.now() } }]);

        // Progress, at most every 150 ms (and always the last event).
        let lastTick = 0;
        const onProgress = (loaded: number, total: number) => {
          const now = Date.now();
          const done = loaded >= total;
          if (!done && now - lastTick < 150) return;
          lastTick = now;
          setDocuments((prev) =>
            prev.map((d) =>
              d.id === tempId && d.uploadProgress
                ? { ...d, uploadProgress: { ...d.uploadProgress, loaded: done ? d.uploadProgress.total : loaded, total: done ? d.uploadProgress.total : total } }
                : d,
            ),
          );
        };

        // Attempt to upload; on success replace the temp entry
        uploadMutation.mutate({ file, onProgress }, {''')
rep('''                      filename: data.filename || d.filename,
                      uploading: false,
                    }''', '''                      filename: data.filename || d.filename,
                      uploading: false,
                      uploadProgress: undefined,
                    }''')
rep('''                d.id === tempId ? { ...d, uploading: false, uploadError: msg } : d,''',
    '''                d.id === tempId ? { ...d, uploading: false, uploadProgress: undefined, uploadError: msg } : d,''')
P.write_text(s, encoding="utf-8")
print("ok")
