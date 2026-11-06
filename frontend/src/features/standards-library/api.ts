// OE-DELIVERY: 2026-10-29-standards-library-v1
/**
 * API helpers for the Standards Library page.
 *
 * Backed by /api/v1/standards-library/ — see
 * backend/app/modules/standards_library/. Structured section tables
 * (AISC shapes, SSMA cold-formed members), MasterFormat divisions and
 * the code-book shelf (list + upload).
 */

import { apiGet, apiPost } from '@/shared/lib/api';

export interface StandardSection {
  id: string;
  source: string;
  standard: string;
  designation: string;
  edi_name: string | null;
  type: string;
  division: string;
  weight_lb_ft: number | null;
  area_in2: number | null;
  depth_in: number | null;
  ix_in4: number | null;
  sx_in3: number | null;
  design_thickness_in: number | null;
  fy_ksi: number | null;
  properties: Record<string, unknown>;
}

export interface DecodedMember {
  designation: string;
  depth_in: number;
  style: string;
  style_name: string;
  flange_in: number;
  mil: number;
  design_thickness_in: number;
  min_thickness_in: number;
  gauge_label: string | null;
}

export interface LookupResult {
  query: string;
  match: StandardSection | null;
  decoded: DecodedMember | null;
}

export interface DivisionEntry {
  code: string;
  title: string;
  kind: string;
  parent_code: string | null;
}

export interface LibraryDocument {
  id: string;
  title: string;
  body: string;
  code: string;
  edition: string;
  division: string;
  page_count: number;
  index_status: string;
}

export interface LibraryIndex {
  divisions: DivisionEntry[];
  sections: DivisionEntry[];
  documents: LibraryDocument[];
  counts: Record<string, number>;
}

export function fetchLibraryIndex(): Promise<LibraryIndex> {
  return apiGet<LibraryIndex>('/v1/standards-library/');
}

export function lookupSection(q: string): Promise<LookupResult> {
  return apiGet<LookupResult>(`/v1/standards-library/sections/lookup/?q=${encodeURIComponent(q)}`);
}

export function searchSections(q: string): Promise<StandardSection[]> {
  return apiGet<StandardSection[]>(
    `/v1/standards-library/sections/search/?q=${encodeURIComponent(q)}&limit=50`,
  );
}

/** Shelve a code-book PDF (multipart). Needs the standards_library.manage grant. */
export function uploadDocument(form: FormData): Promise<LibraryDocument> {
  return apiPost<LibraryDocument>('/v1/standards-library/documents/', form);
}
