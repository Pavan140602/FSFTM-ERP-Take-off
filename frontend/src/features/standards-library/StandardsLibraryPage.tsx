// OE-DELIVERY: 2026-10-29-standards-library-v1
/**
 * Standards Library — codes and standards reference for estimating.
 *
 * One designation lookup over the structured section tables (AISC
 * Shapes Database v16.0 + SSMA Technical Guide): type a member exactly
 * as the drawing prints it (HSS6X2X1/8, W10X26, 600S162-54) and get its
 * published weight and properties. SSMA designations that are not in
 * the seeded tables are decoded from the designation system instead of
 * returning nothing. The page also carries the MasterFormat division
 * index used for scope tagging and the code-book shelf (AISC 360,
 * AISI S100, AWS, OSHA) that Ask-the-Code will read.
 *
 * Data: GET /api/v1/standards-library/ (read-only).
 * Visibility is governed by the 'standards_library' module grant
 * (Users -> Role Module Access) — see ModuleRouteGate in App.tsx.
 */

import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { BookOpen, FileText, Info, Search } from 'lucide-react';
import {
  fetchLibraryIndex,
  lookupSection,
  searchSections,
  uploadDocument,
  type DecodedMember,
  type StandardSection,
} from './api';

/* ── helpers ─────────────────────────────────────────────────────── */

// MasterFormat sections FSFTM scopes first (cold-formed steel package).
const FSFTM_PRIMARY = new Set(['05 40 00', '05 41 00', '05 42 00', '05 43 00', '09 22 16']);

function fmt(value: number | null, digits = 3): string {
  if (value === null || value === undefined) return '—';
  const v = Number(value.toFixed(digits));
  return String(v);
}

function fmtCount(value: number): string {
  return value.toLocaleString('en-US');
}

const CARD =
  'rounded-xl border border-gray-200 bg-white shadow-sm dark:border-gray-800 dark:bg-gray-900';
const HEAD = 'text-sm font-bold text-gray-900 dark:text-gray-100';
const SUB = 'text-xs text-gray-500 dark:text-gray-400';
const CELL = 'px-3 py-2 text-sm text-gray-900 dark:text-gray-100';
const TH =
  'px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400';

/* ── result cards ────────────────────────────────────────────────── */

function Stat({ label, value, unit }: { label: string; value: string; unit?: string }) {
  return (
    <div className="rounded-lg bg-gray-50 px-3 py-2 dark:bg-gray-800/60">
      <div className="text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
        {label}
      </div>
      <div className="mt-0.5 text-base font-semibold text-gray-900 dark:text-gray-100">
        {value}
        {unit ? <span className="ml-1 text-xs font-normal text-gray-500 dark:text-gray-400">{unit}</span> : null}
      </div>
    </div>
  );
}

function MatchCard({ section }: { section: StandardSection }) {
  const [showAll, setShowAll] = useState(false);
  const entries = Object.entries(section.properties || {})
    .filter(([, v]) => v !== null && v !== undefined && v !== '')
    .sort(([a], [b]) => a.localeCompare(b));
  const visible = showAll ? entries : entries.slice(0, 24);
  return (
    <div className={`${CARD} px-5 py-4`}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-lg font-bold text-gray-900 dark:text-gray-100">{section.designation}</span>
        <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-500/15 dark:text-blue-400">
          {section.source}
        </span>
        {section.division ? (
          <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600 dark:bg-gray-800 dark:text-gray-300">
            Division {section.division}
          </span>
        ) : null}
        {section.edi_name && section.edi_name !== section.designation ? (
          <span className={SUB}>EDI: {section.edi_name}</span>
        ) : null}
      </div>
      <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">{section.standard}</div>
      <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
        <Stat label="Weight" value={fmt(section.weight_lb_ft)} unit="lb/ft" />
        <Stat label="Area" value={fmt(section.area_in2)} unit="in²" />
        <Stat label="Depth" value={fmt(section.depth_in)} unit="in" />
        <Stat label="Ix" value={fmt(section.ix_in4)} unit="in⁴" />
        <Stat label="Sx" value={fmt(section.sx_in3)} unit="in³" />
        {section.design_thickness_in !== null ? (
          <Stat label="Thickness" value={fmt(section.design_thickness_in, 4)} unit="in" />
        ) : (
          <Stat label="Type" value={section.type || '—'} />
        )}
      </div>
      {entries.length > 0 ? (
        <div className="mt-4">
          {entries.length > 24 ? (
            <button
              type="button"
              onClick={() => setShowAll((v) => !v)}
              className="text-sm font-medium text-blue-600 hover:underline dark:text-blue-400"
            >
              {showAll ? 'Hide full properties' : `Full properties (${entries.length})`}
            </button>
          ) : null}
          {showAll || entries.length <= 24 ? (
            <div className="mt-2 grid grid-cols-2 gap-x-6 gap-y-1 sm:grid-cols-3 lg:grid-cols-4">
              {visible.map(([k, v]) => (
                <div key={k} className="flex items-baseline justify-between gap-2 text-sm">
                  <span className="text-gray-500 dark:text-gray-400">{k}</span>
                  <span className="font-medium text-gray-900 dark:text-gray-100">{String(v)}</span>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function DecodedCard({ decoded }: { decoded: DecodedMember }) {
  return (
    <div className="rounded-xl border border-amber-200 bg-amber-50 px-5 py-4 shadow-sm dark:border-amber-500/30 dark:bg-amber-500/10">
      <div className="flex items-start gap-2.5">
        <Info className="mt-0.5 h-5 w-5 flex-none text-amber-600 dark:text-amber-400" />
        <div className="min-w-0">
          <div className="text-base font-bold text-gray-900 dark:text-gray-100">
            {decoded.designation} — decoded, not in the seeded tables
          </div>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">
            This SSMA designation is not one of the published property rows, so there is no listed
            weight for it. Its geometry comes from the SSMA designation system:
          </p>
          <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
            <Stat label="Style" value={decoded.style_name} />
            <Stat label="Depth" value={fmt(decoded.depth_in)} unit="in" />
            <Stat label="Flange" value={fmt(decoded.flange_in)} unit="in" />
            <Stat label="Design thickness" value={fmt(decoded.design_thickness_in, 4)} unit="in" />
            <Stat label="Min thickness" value={fmt(decoded.min_thickness_in, 4)} unit="in" />
            <Stat label="Gauge" value={decoded.gauge_label || '—'} />
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── page ────────────────────────────────────────────────────────── */

export function StandardsLibraryPage() {
  const [query, setQuery] = useState('');
  const [submitted, setSubmitted] = useState('');

  const queryClient = useQueryClient();
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
      form.append('title', docTitle.trim() || docFile.name.replace(/\.pdf$/i, ''));
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

  const indexQuery = useQuery({ queryKey: ['standards-library-index'], queryFn: fetchLibraryIndex });
  const searchQuery = useQuery({
    queryKey: ['standards-library-search', query.trim()],
    queryFn: () => searchSections(query.trim()),
    enabled: query.trim().length >= 2,
  });
  const lookupQuery = useQuery({
    queryKey: ['standards-library-lookup', submitted],
    queryFn: () => lookupSection(submitted),
    enabled: submitted !== '',
  });

  const runLookup = (text: string) => {
    const t = text.trim();
    if (t) setSubmitted(t);
  };

  const pickRow = (section: StandardSection) => {
    setQuery(section.designation);
    setSubmitted(section.designation);
  };

  const index = indexQuery.data;
  const lookup = lookupQuery.data;
  const results = searchQuery.data || [];

  return (
    <div className="mx-auto w-full max-w-7xl px-4 py-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-xl font-bold text-gray-900 dark:text-gray-100">
            <BookOpen className="h-6 w-6" /> Standards Library
          </h1>
          <p className={SUB}>
            AISC shapes and SSMA cold-formed members with published properties, MasterFormat
            divisions, and the code-book shelf.
          </p>
        </div>
        {index ? (
          <div className="flex flex-wrap gap-2">
            {Object.entries(index.counts).map(([source, count]) => (
              <span
                key={source}
                className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-700 dark:bg-gray-800 dark:text-gray-200"
              >
                {source}: {fmtCount(Number(count))} sections
              </span>
            ))}
          </div>
        ) : null}
      </div>

      <div className="mt-5 grid grid-cols-1 gap-4 lg:grid-cols-[1fr_320px]">
        <div className="min-w-0">
          <div className={`${CARD} px-5 py-4`}>
            <div className={HEAD}>Member lookup</div>
            <p className={SUB}>
              Type a designation exactly as the drawing prints it — try HSS6X2X1/8, W10X26 or
              600S162-54 — then press Enter for the full record.
            </p>
            <div className="relative mt-3">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') runLookup(query);
                }}
                placeholder="Search a designation, e.g. HSS6X2X1/8"
                className="w-full rounded-lg border border-gray-300 bg-white py-2 pl-9 pr-3 text-sm text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:outline-none dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
              />
            </div>
            {query.trim().length >= 2 ? (
              <div className="mt-3 overflow-x-auto">
                {searchQuery.isLoading ? (
                  <div className={SUB}>Searching…</div>
                ) : results.length === 0 ? (
                  <div className={SUB}>
                    No table matches — press Enter to try an exact lookup or an SSMA decode.
                  </div>
                ) : (
                  <table className="w-full border-collapse">
                    <thead>
                      <tr className="border-b border-gray-200 dark:border-gray-800">
                        <th className={TH}>Designation</th>
                        <th className={TH}>Source</th>
                        <th className={TH}>Division</th>
                        <th className={TH}>Weight (lb/ft)</th>
                        <th className={TH}>Area (in²)</th>
                        <th className={TH}>Depth (in)</th>
                        <th className={TH}>Ix (in⁴)</th>
                        <th className={TH}>Sx (in³)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {results.map((r) => (
                        <tr
                          key={r.id}
                          onClick={() => pickRow(r)}
                          className="cursor-pointer border-b border-gray-100 transition-colors last:border-0 hover:bg-gray-50 dark:border-gray-800/70 dark:hover:bg-gray-800/40"
                        >
                          <td className={`${CELL} font-semibold`}>{r.designation}</td>
                          <td className={CELL}>{r.source}</td>
                          <td className={CELL}>{r.division || '—'}</td>
                          <td className={CELL}>{fmt(r.weight_lb_ft)}</td>
                          <td className={CELL}>{fmt(r.area_in2)}</td>
                          <td className={CELL}>{fmt(r.depth_in)}</td>
                          <td className={CELL}>{fmt(r.ix_in4)}</td>
                          <td className={CELL}>{fmt(r.sx_in3)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            ) : null}
          </div>

          <div className="mt-4">
            {lookupQuery.isLoading ? (
              <div className={`${CARD} px-5 py-4 ${SUB}`}>Looking up {submitted}…</div>
            ) : lookup ? (
              lookup.match ? (
                <MatchCard section={lookup.match} />
              ) : lookup.decoded ? (
                <DecodedCard decoded={lookup.decoded} />
              ) : (
                <div className={`${CARD} px-5 py-4`}>
                  <span className={SUB}>
                    No match for “{lookup.query}” in the library, and it is not an SSMA
                    designation. Check the spelling against the drawing.
                  </span>
                </div>
              )
            ) : null}
          </div>

          <div className={`${CARD} mt-4 px-5 py-4`}>
            <div className={HEAD}>Code-book shelf</div>
            <p className={SUB}>
              The standards the panel answers from — Ask-the-Code reads these with page citations.
            </p>
            {index && index.documents.length > 0 ? (
              <div className="mt-3 space-y-2">
                {index.documents.map((d) => (
                  <div key={d.id} className="flex items-center gap-3 text-sm">
                    <FileText className="h-4 w-4 flex-none text-gray-400" />
                    <span className="font-medium text-gray-900 dark:text-gray-100">{d.title}</span>
                    <span className={SUB}>
                      {[d.code, d.edition].filter(Boolean).join(' ')}
                      {d.page_count ? ` · ${d.page_count} pages` : ''} · {d.index_status}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-3 text-sm text-gray-600 dark:text-gray-300">
                No code books on the shelf yet. OSHA is fetched free by script; paid standards
                (AISC 360, AISI S100, AWS D1.1/D1.3) are uploaded from company copies with the
                add form below.
              </p>
            )}
          </div>

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

        <div className={`${CARD} h-fit px-5 py-4`}>
          <div className={HEAD}>MasterFormat divisions</div>
          <p className={SUB}>Sections FSFTM scopes under are marked.</p>
          {indexQuery.isLoading ? (
            <div className={`${SUB} mt-3`}>Loading…</div>
          ) : index ? (
            <div className="mt-3 space-y-2.5">
              {index.divisions.map((d) => (
                <div key={d.code}>
                  <div className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                    {d.code} — {d.title}
                  </div>
                  {index.sections
                    .filter((s) => s.parent_code === d.code)
                    .map((s) => (
                      <div key={s.code} className="ml-3 flex items-center gap-2 text-sm">
                        <span className="text-gray-600 dark:text-gray-300">
                          {s.code} {s.title}
                        </span>
                        {FSFTM_PRIMARY.has(s.code) ? (
                          <span className="rounded-full bg-green-100 px-1.5 py-0.5 text-[10px] font-semibold text-green-700 dark:bg-green-500/15 dark:text-green-400">
                            FSFTM
                          </span>
                        ) : null}
                      </div>
                    ))}
                </div>
              ))}
            </div>
          ) : (
            <div className={`${SUB} mt-3`}>Could not load the division index.</div>
          )}
        </div>
      </div>
    </div>
  );
}
