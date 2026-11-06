"""Add the code-book upload form to the Standards Library page.

OE-DELIVERY: 2026-10-29-standards-library-v1

Anchored insertions into the chunk-2 StandardsLibraryPage.tsx, each
verified before anything is written:
  1. useQueryClient import;
  2. uploadDocument API import (needs the v2 api.ts delivered with
     chunk 4 - replace the file first);
  3. upload form state + submit handler;
  4. corrected empty-shelf wording;
  5. the "Add a code book" card under the shelf card.

Idempotent: if the form is already present it prints so and exits. If
an anchor is missing or not unique it writes nothing and says which
anchor failed - send that output back instead of editing by hand.

Run from the repo root with plain python (stdlib only):
    python patch_page_upload.py
No restart needed - Vite picks the change up; hard-refresh the tab.
"""

from __future__ import annotations

from pathlib import Path

TARGET = Path("frontend/src/features/standards-library/StandardsLibraryPage.tsx")
MARKER = "Add a code book"

E1_ANCHOR = "import { useQuery } from '@tanstack/react-query';"
E1_NEW = "import { useQuery, useQueryClient } from '@tanstack/react-query';"

E2_ANCHOR = "  searchSections,\n"
E2_NEW = "  searchSections,\n  uploadDocument,\n"

E3_ANCHOR = "  const indexQuery = useQuery({ queryKey: ['standards-library-index'], queryFn: fetchLibraryIndex });"
E3_ADD = """  const queryClient = useQueryClient();
  const FIELD =
    'mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-blue-500 focus:outline-none dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100';
  const [docTitle, setDocTitle] = useState('');
  const [docBody, setDocBody] = useState('AISC');
  const [docCode, setDocCode] = useState('');
  const [docEdition, setDocEdition] = useState('');
  const [docDivision, setDocDivision] = useState('');
  const [docFile, setDocFile] = useState<File | null>(null);
  const [fileKey, setFileKey] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState('');

  const submitUpload = async () => {
    if (!docFile || uploading) return;
    setUploading(true);
    setUploadMsg('');
    try {
      const form = new FormData();
      form.append('file', docFile);
      form.append('title', docTitle.trim() || docFile.name.replace(/\\.pdf$/i, ''));
      form.append('body', docBody);
      form.append('code', docCode.trim());
      form.append('edition', docEdition.trim());
      form.append('division', docDivision);
      const saved = await uploadDocument(form);
      setUploadMsg(`Added to the shelf: ${saved.title} (${saved.page_count} pages).`);
      setDocTitle('');
      setDocCode('');
      setDocEdition('');
      setDocDivision('');
      setDocFile(null);
      setFileKey((k) => k + 1);
      await queryClient.invalidateQueries({ queryKey: ['standards-library-index'] });
    } catch (err) {
      setUploadMsg(
        `Upload failed: ${err instanceof Error ? err.message : 'unknown error'} - adding books needs the standards_library.manage grant.`,
      );
    } finally {
      setUploading(false);
    }
  };

"""

E4_ANCHOR = """                No code books on the shelf yet. Free standards (OSHA) will be fetched for you;
                paid standards (AISC 360, AISI S100, AWS D1.1/D1.3) are uploaded from company
                copies — the upload arrives with the document-shelf update."""
E4_NEW = """                No code books on the shelf yet. OSHA is fetched free by script; paid standards
                (AISC 360, AISI S100, AWS D1.1/D1.3) are uploaded from company copies with the
                add form below."""

E5_ANCHOR = "          </div>\n        </div>\n\n        <div className={`${CARD} h-fit px-5 py-4`}>"
E5_NEW = """          </div>

          <div className={`${CARD} mt-4 px-5 py-4`}>
            <div className={HEAD}>Add a code book</div>
            <p className={SUB}>
              Shelve a standard the company owns (PDF). Adding books needs the
              standards_library.manage grant.
            </p>
            <div className="mt-3 grid grid-cols-2 gap-2">
              <label className="col-span-2 block">
                <span className={SUB}>Title</span>
                <input value={docTitle} onChange={(e) => setDocTitle(e.target.value)} placeholder="e.g. Specification for Structural Steel Buildings" className={FIELD} />
              </label>
              <label className="block">
                <span className={SUB}>Body</span>
                <select value={docBody} onChange={(e) => setDocBody(e.target.value)} className={FIELD}>
                  {['AISC', 'AISI', 'AWS', 'OSHA', 'ASTM', 'Other'].map((b) => (
                    <option key={b} value={b}>{b}</option>
                  ))}
                </select>
              </label>
              <label className="block">
                <span className={SUB}>Code</span>
                <input value={docCode} onChange={(e) => setDocCode(e.target.value)} placeholder="e.g. AISC 360" className={FIELD} />
              </label>
              <label className="block">
                <span className={SUB}>Edition</span>
                <input value={docEdition} onChange={(e) => setDocEdition(e.target.value)} placeholder="e.g. 2022" className={FIELD} />
              </label>
              <label className="block">
                <span className={SUB}>Division</span>
                <select value={docDivision} onChange={(e) => setDocDivision(e.target.value)} className={FIELD}>
                  <option value="">-</option>
                  {(index?.sections || []).map((s) => (
                    <option key={s.code} value={s.code}>{s.code} {s.title}</option>
                  ))}
                </select>
              </label>
              <label className="col-span-2 block">
                <span className={SUB}>PDF file</span>
                <input key={fileKey} type="file" accept="application/pdf" onChange={(e) => setDocFile(e.target.files?.[0] || null)} className="mt-1 block w-full text-sm text-gray-600 dark:text-gray-300" />
              </label>
            </div>
            <div className="mt-3 flex items-center gap-3">
              <button type="button" onClick={submitUpload} disabled={!docFile || uploading} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50">
                {uploading ? 'Uploading...' : 'Add to shelf'}
              </button>
              {uploadMsg ? <span className="text-sm text-gray-600 dark:text-gray-300">{uploadMsg}</span> : null}
            </div>
          </div>
        </div>

        <div className={`${CARD} h-fit px-5 py-4`}>"""


def main() -> None:
    if not TARGET.exists():
        raise SystemExit(f"NOT FOUND: {TARGET} - run this from the repo root.")
    text = TARGET.read_text(encoding="utf-8")
    if MARKER in text:
        print("Already applied - the upload form is already on the page. Nothing changed.")
        return
    edits = [
        ("react-query import", E1_ANCHOR, E1_NEW),
        ("api import", E2_ANCHOR, E2_NEW),
        ("upload state", E3_ANCHOR, E3_ADD + E3_ANCHOR),
        ("shelf wording", E4_ANCHOR, E4_NEW),
        ("upload card", E5_ANCHOR, E5_NEW),
    ]
    for name, anchor, _ in edits:
        count = text.count(anchor)
        if count != 1:
            raise SystemExit(
                f"ANCHOR MISSING ({name}): found {count} copies, need exactly 1. "
                "Nothing was written - send this output back."
            )
    for _, anchor, replacement in edits:
        text = text.replace(anchor, replacement, 1)
    TARGET.write_text(text, encoding="utf-8")
    print(f"Patched OK - StandardsLibraryPage.tsx now {text.count(chr(10)) + 1} lines. Hard-refresh the browser tab (Ctrl+Shift+R).")


if __name__ == "__main__":
    main()
