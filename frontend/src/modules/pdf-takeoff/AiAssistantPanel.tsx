// OE-DELIVERY: 2026-10-29-doc-intel-v3-highlight-fix2 (was 2026-10-29-doc-intel-v3-highlight-fix)
import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { Loader2, Search, Sparkles } from 'lucide-react';
import { apiGet, apiPost } from '../../shared/lib/api';

/** AI Assistant tab content for the PDF Measurements right panel.
 *
 * Works on the document the viewer already has open. Search and Ask run
 * against the per-page text the takeoff upload flow extracted
 * (TakeoffDocument.page_data), served by the takeoff module's doc-intel
 * endpoints - no new extraction pipeline, no new table. A click on a
 * search result or an Ask citation jumps the viewer to that page via
 * onJumpToPage (the viewer's own goToPage), so the estimator never
 * leaves the drawing. AI answers are suggestions only: the drawing is
 * right there, and nothing posts to estimation until the estimator
 * confirms it.
 *
 * Local files (documentId null) have no server document, so the panel
 * explains the upload-first flow instead of calling endpoints that
 * would 404.
 *
 * v2 (2026-10-29): theme-surface inputs/selects (no white boxes in the
 * dark theme), free-first provider labels including Kimi, the picked
 * provider is remembered in localStorage, provider errors are mapped
 * to plain guidance (free-limit reached / paid credits), and a Today
 * card shows the signed-in user's panel activity for the day
 * (searches, asks by provider, OCR runs) from the activity endpoint.
 *
 * v3 (2026-10-29): result and citation clicks highlight the term ON
 * the drawing through the viewer's built-in find machinery (the
 * onHighlightTerm prop) instead of only jumping pages; a Clear
 * highlight row appears while a highlight is on. Without the prop
 * (older viewer) clicks keep the plain page-jump behaviour.
 */

export interface AiAssistantPanelProps {
  /** Server takeoff document id, or null for a fresh local drop. */
  documentId: string | null;
  /** 1-based page the viewer is showing now. */
  currentPage: number;
  /** Jump the viewer to a 1-based page (the viewer's goToPage). */
  onJumpToPage: (page: number) => void;
  /** Highlight a term on a page via the viewer's built-in find (optional;
   * when absent, clicks fall back to a plain page jump). */
  onHighlightTerm?: (term: string, page: number) => void;
  /** Clear a highlight previously set via onHighlightTerm. */
  onClearHighlight?: () => void;
}

interface DocIntelPageRow {
  page: number;
  has_text: boolean;
  chars: number;
  ocr: boolean;
}

interface DocIntelSummary {
  document_id: string;
  filename: string;
  index_available: boolean;
  page_count: number;
  readable_pages: number;
  scanned_pages: number;
  pages: DocIntelPageRow[];
  ocr: { built_pages: number; status: string | null };
}

interface SearchMatch {
  page: number;
  snippet: string;
}

interface AskResponse {
  answer: string;
  citations: number[];
  model: string;
  provider: string;
}

interface TodayActivity {
  date: string;
  searches: number;
  asks: number;
  ocr_runs: number;
  documents: number;
  by_provider: Record<string, number>;
  recent: { time: string; action: string; document_name: string; summary: string }[];
}

const PROVIDER_OPTIONS: { value: string; label: string }[] = [
  { value: 'groq', label: 'Groq - free' },
  { value: 'gemini', label: 'Google Gemini - free' },
  { value: 'openrouter', label: 'OpenRouter - free models' },
  { value: 'kimi', label: 'Kimi (Moonshot) - free tier' },
  { value: 'ollama', label: 'Ollama - local, no key' },
  { value: 'anthropic', label: 'Anthropic Claude - paid credits' },
  { value: 'openai', label: 'OpenAI - paid credits' },
];

const PROVIDER_STORAGE_KEY = 'takeoff.aiPanel.provider';

function errorMessage(err: unknown): string {
  if (err instanceof Error) return err.message;
  if (typeof err === 'string') return err;
  return 'Request failed';
}

function friendlyAskError(message: string): string {
  const lower = message.toLowerCase();
  if (
    lower.includes('429') ||
    lower.includes('rate limit') ||
    lower.includes('rate_limit') ||
    lower.includes('quota')
  ) {
    return (
      'Free limit reached for this provider for now. Switch to another free provider above and ask ' +
      'again - the limit resets on its own (hourly/daily), no payment needed. Details: ' +
      message
    );
  }
  if (lower.includes('credit balance') || lower.includes('credits')) {
    return (
      'This provider needs paid credits, which are not available. Pick a free provider above ' +
      '(Groq, Gemini, OpenRouter, Kimi) and ask again. Details: ' +
      message
    );
  }
  if (lower.includes('no api key configured')) {
    return (
      message +
      ' Free keys: Groq (console.groq.com), Gemini (aistudio.google.com), Kimi (platform.moonshot.ai).'
    );
  }
  return message;
}

const QUESTION_STOPWORDS = new Set(
  (
    'a an the and or of to in on for with is are was were be by at from ' +
    'what where which when who why how ' +
    'show find search locate look looking get give tell list check highlight mark open go ' +
    'me my it its this that these those there here any all many much does do did can could please'
  ).split(' '),
);

/** The term worth highlighting for an Ask citation: the LONGEST
 * significant word of the question. Tokens split on whitespace only
 * (edge punctuation trimmed), so a member designation keeps its
 * fraction: "where is the HSS6X2X1/8" gives "HSS6X2X1/8", not
 * "HSS6X2X1". Action words and grammar words are filtered out first,
 * so "search the summary" gives "summary" (not "search"). */
function termFromQuestion(question: string): string {
  const tokens = (question || '')
    .split(/\s+/)
    .map((token) => token.replace(/^[^A-Za-z0-9]+/, '').replace(/[^A-Za-z0-9]+$/, ''))
    .filter(Boolean);
  const significant = tokens.filter(
    (token) => token.length >= 3 && !QUESTION_STOPWORDS.has(token.toLowerCase()),
  );
  if (significant.length === 0) return tokens[0] || (question || '').trim();
  return significant.reduce((best, token) => (token.length > best.length ? token : best), significant[0]!);
}

export default function AiAssistantPanel({
  documentId,
  currentPage,
  onJumpToPage,
  onHighlightTerm,
  onClearHighlight,
}: AiAssistantPanelProps) {
  const [summary, setSummary] = useState<DocIntelSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [mode, setMode] = useState<'search' | 'ask'>('search');
  const [query, setQuery] = useState('');
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [matches, setMatches] = useState<SearchMatch[] | null>(null);
  const [searchedQuery, setSearchedQuery] = useState('');
  const [provider, setProvider] = useState<string>(() => {
    try {
      return window.localStorage.getItem(PROVIDER_STORAGE_KEY) || 'groq';
    } catch {
      return 'groq';
    }
  });
  const [today, setToday] = useState<TodayActivity | null>(null);
  const [askedQuestion, setAskedQuestion] = useState('');
  const [highlightActive, setHighlightActive] = useState(false);
  const [question, setQuestion] = useState('');
  const [asking, setAsking] = useState(false);
  const [askError, setAskError] = useState<string | null>(null);
  const [askResult, setAskResult] = useState<AskResponse | null>(null);
  const [ocrStarting, setOcrStarting] = useState(false);
  const [ocrMessage, setOcrMessage] = useState<string | null>(null);
  const [ocrPolling, setOcrPolling] = useState(false);
  const ocrPollsRef = useRef(0);

  const loadSummary = useCallback(async () => {
    if (!documentId) return;
    setSummaryLoading(true);
    setSummaryError(null);
    try {
      const data = await apiGet<DocIntelSummary>(`/v1/takeoff/documents/${documentId}/doc-intel/`);
      setSummary(data);
    } catch (err: unknown) {
      setSummaryError(errorMessage(err));
    } finally {
      setSummaryLoading(false);
    }
  }, [documentId]);

  const loadToday = useCallback(async () => {
    try {
      const data = await apiGet<TodayActivity>('/v1/takeoff/doc-intel/activity/today/');
      setToday(data);
    } catch {
      // Backend not patched yet - the Today card simply stays hidden.
      setToday(null);
    }
  }, []);

  useEffect(() => {
    setSummary(null);
    setMatches(null);
    setAskResult(null);
    setAskedQuestion('');
    setHighlightActive(false);
    setOcrPolling(false);
    setToday(null);
    if (documentId) {
      void loadSummary();
      void loadToday();
    }
  }, [documentId, loadSummary, loadToday]);

  useEffect(() => {
    if (!ocrPolling || !documentId) return;
    ocrPollsRef.current = 0;
    const timer = window.setInterval(() => {
      ocrPollsRef.current += 1;
      void loadSummary().then(() => {
        if (ocrPollsRef.current >= 100) setOcrPolling(false);
      });
    }, 3000);
    return () => window.clearInterval(timer);
  }, [ocrPolling, documentId, loadSummary]);

  useEffect(() => {
    if (!ocrPolling || !summary) return;
    if (summary.ocr.status === 'ready' || summary.ocr.status === 'failed') setOcrPolling(false);
  }, [ocrPolling, summary]);

  const runSearch = useCallback(
    async (event?: FormEvent) => {
      if (event) event.preventDefault();
      if (!documentId || !query.trim() || searching) return;
      setSearching(true);
      if (onClearHighlight) onClearHighlight();
      setHighlightActive(false);
      setSearchError(null);
      try {
        const data = await apiGet<{ query: string; matches: SearchMatch[] }>(
          `/v1/takeoff/documents/${documentId}/doc-intel/search/?q=${encodeURIComponent(query.trim())}`,
        );
        setMatches(data.matches);
        setSearchedQuery(data.query);
        void loadToday();
      } catch (err: unknown) {
        setSearchError(errorMessage(err));
      } finally {
        setSearching(false);
      }
    },
    [documentId, query, searching, loadToday, onClearHighlight],
  );

  const runAsk = useCallback(
    async (event?: FormEvent) => {
      if (event) event.preventDefault();
      if (!documentId || !question.trim() || asking) return;
      setAsking(true);
      setAskError(null);
      try {
        const data = await apiPost<AskResponse, { provider: string; question: string }>(
          `/v1/takeoff/documents/${documentId}/doc-intel/ask/`,
          { provider, question: question.trim() },
        );
        setAskResult(data);
        setAskedQuestion(question.trim());
        void loadToday();
      } catch (err: unknown) {
        setAskError(friendlyAskError(errorMessage(err)));
      } finally {
        setAsking(false);
      }
    },
    [documentId, question, asking, provider, loadToday],
  );

  const runOcr = useCallback(async () => {
    if (!documentId || ocrStarting) return;
    setOcrStarting(true);
    setOcrMessage(null);
    try {
      const data = await apiPost<{ started: boolean; ocr_available: boolean; message?: string }, Record<string, never>>(
        `/v1/takeoff/documents/${documentId}/doc-intel/ocr/`,
        {},
      );
      if (!data.started) {
        setOcrMessage(data.message || 'OCR could not start.');
      } else {
        setOcrMessage('OCR running in the background — this panel refreshes when it finishes.');
        setOcrPolling(true);
        void loadToday();
      }
    } catch (err: unknown) {
      setOcrMessage(errorMessage(err));
    } finally {
      setOcrStarting(false);
    }
  }, [documentId, ocrStarting, loadToday]);

  const handleMatchClick = useCallback(
    (match: SearchMatch) => {
      if (onHighlightTerm) {
        onHighlightTerm(searchedQuery, match.page);
        setHighlightActive(true);
      } else {
        onJumpToPage(match.page);
      }
    },
    [onHighlightTerm, onJumpToPage, searchedQuery],
  );

  const handleCitationClick = useCallback(
    (page: number) => {
      if (onHighlightTerm) {
        onHighlightTerm(termFromQuestion(askedQuestion), page);
        setHighlightActive(true);
      } else {
        onJumpToPage(page);
      }
    },
    [onHighlightTerm, onJumpToPage, askedQuestion],
  );

  const handleClearHighlight = useCallback(() => {
    if (onClearHighlight) onClearHighlight();
    setHighlightActive(false);
  }, [onClearHighlight]);

  if (!documentId) {
    return (
      <div className="rounded-md border border-border/80 bg-surface-primary/80 p-3 shadow-sm">
        <p className="text-sm font-semibold text-content-primary">AI Assistant needs a server document</p>
        <p className="mt-1 text-xs leading-relaxed text-content-secondary">
          This PDF was opened as a local file, so the server has no text index for it yet. Upload it to the
          project once (filmstrip or Step 1 Upload PDF), then reopen it here — search and Ask AI will work on
          it, and your markups will persist server-side.
        </p>
      </div>
    );
  }

  if (summaryLoading && !summary) {
    return (
      <div className="flex items-center gap-2 rounded-md border border-border/80 bg-surface-primary/80 p-3 text-xs text-content-secondary shadow-sm">
        <Loader2 size={14} className="animate-spin" /> Loading document index…
      </div>
    );
  }

  if (summaryError && !summary) {
    return (
      <div className="rounded-md border border-border/80 bg-surface-primary/80 p-3 shadow-sm">
        <p className="text-xs text-red-500">{summaryError}</p>
        <button
          type="button"
          onClick={() => void loadSummary()}
          className="mt-2 rounded bg-oe-blue px-2.5 py-1 text-xs font-semibold text-white"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!summary) return null;

  return (
    <div className="space-y-3">
      <div className="rounded-md border border-border/80 bg-surface-primary/80 p-3 shadow-sm">
        <p className="text-[10px] font-bold uppercase tracking-widest text-content-tertiary">This document</p>
        <p className="mt-1 truncate text-xs font-semibold text-content-primary" title={summary.filename}>
          {summary.filename || 'Untitled document'}
        </p>
        <p className="mt-1 text-xs text-content-secondary">
          {summary.page_count} pages · {summary.readable_pages} readable · {summary.scanned_pages} scanned
          {summary.ocr.built_pages > 0 ? ` · OCR text on ${summary.ocr.built_pages} pages` : ''}
        </p>
        <p className="mt-1 text-xs text-content-secondary">
          Now viewing: Page {currentPage} of {summary.page_count}
        </p>
        {!summary.index_available ? (
          <p className="mt-2 text-xs text-amber-700">
            No extracted text for this document yet — it may be an older upload. Re-uploading it will extract
            the text.
          </p>
        ) : null}
        {summary.scanned_pages > 0 && summary.ocr.status !== 'ready' ? (
          <div className="mt-2">
            <button
              type="button"
              onClick={() => void runOcr()}
              disabled={ocrStarting || ocrPolling}
              className="rounded bg-oe-blue px-2.5 py-1 text-xs font-semibold text-white disabled:opacity-50"
            >
              {ocrStarting || ocrPolling ? 'OCR running…' : 'Run OCR for scanned pages'}
            </button>
            {ocrMessage ? <p className="mt-1 text-xs text-content-secondary">{ocrMessage}</p> : null}
          </div>
        ) : null}
      </div>

      <div className="flex rounded-md border border-border/80 bg-surface-primary/80 p-1 shadow-sm" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={mode === 'search'}
          onClick={() => setMode('search')}
          className={`flex-1 rounded px-2 py-1 text-[11px] font-semibold transition-colors ${
            mode === 'search' ? 'bg-oe-blue text-white shadow-sm' : 'text-content-secondary hover:bg-surface-secondary'
          }`}
        >
          Search
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === 'ask'}
          onClick={() => setMode('ask')}
          className={`flex-1 rounded px-2 py-1 text-[11px] font-semibold transition-colors ${
            mode === 'ask' ? 'bg-oe-blue text-white shadow-sm' : 'text-content-secondary hover:bg-surface-secondary'
          }`}
        >
          Ask AI
        </button>
      </div>

      {highlightActive && onClearHighlight ? (
        <div className="flex items-center justify-between rounded-md border border-border/70 bg-surface-secondary px-2 py-1.5">
          <span className="text-[11px] text-content-secondary">Highlight is on the drawing.</span>
          <button
            type="button"
            onClick={handleClearHighlight}
            className="text-[11px] font-semibold text-oe-blue"
          >
            Clear highlight
          </button>
        </div>
      ) : null}

      {mode === 'search' ? (
        <div>
          <form onSubmit={(event) => void runSearch(event)} className="flex gap-1.5">
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="e.g. CFS, stud, track"
              className="min-w-0 flex-1 rounded-md border border-border bg-surface-secondary px-2 py-1.5 text-xs text-content-primary placeholder:text-content-tertiary"
            />
            <button
              type="submit"
              disabled={searching || !query.trim()}
              className="inline-flex items-center gap-1 rounded-md bg-oe-blue px-2.5 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
            >
              {searching ? <Loader2 size={13} className="animate-spin" /> : <Search size={13} />}
              Search
            </button>
          </form>
          {searchError ? <p className="mt-2 text-xs text-red-500">{searchError}</p> : null}
          {matches !== null ? (
            <div className="mt-2 space-y-1.5">
              <p className="text-xs text-content-secondary">
                {matches.length === 0
                  ? `No matches for “${searchedQuery}”.`
                  : `${matches.length} match${matches.length === 1 ? '' : 'es'} — click one to ${
                      onHighlightTerm ? 'highlight it on that page' : 'jump to that page'
                    }.`}
              </p>
              {matches.map((match) => (
                <button
                  key={match.page}
                  type="button"
                  onClick={() => handleMatchClick(match)}
                  className="block w-full rounded-md border border-border/70 bg-surface-secondary p-2 text-left hover:border-oe-blue/60"
                >
                  <span className="text-xs font-bold text-oe-blue">Page {match.page} →</span>
                  <span className="mt-0.5 block text-xs leading-relaxed text-content-secondary">{match.snippet}</span>
                </button>
              ))}
            </div>
          ) : null}
        </div>
      ) : (
        <div>
          <label className="text-[10px] font-bold uppercase tracking-widest text-content-tertiary" htmlFor="ai-panel-provider">
            AI model (free models first)
          </label>
          <select
            id="ai-panel-provider"
            value={provider}
            onChange={(event) => {
              setProvider(event.target.value);
              try {
                window.localStorage.setItem(PROVIDER_STORAGE_KEY, event.target.value);
              } catch {
                // Storage unavailable (private mode etc.) - persistence is a convenience only.
              }
            }}
            className="mt-1 w-full rounded-md border border-border bg-surface-secondary px-2 py-1.5 text-xs text-content-primary"
          >
            {PROVIDER_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <p className="mt-1 text-xs text-content-secondary">Uses your saved key from Settings → AI.</p>
          <form onSubmit={(event) => void runAsk(event)} className="mt-2">
            <input
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="e.g. Where are the CFS stud walls?"
              className="w-full rounded-md border border-border bg-surface-secondary px-2 py-1.5 text-xs text-content-primary placeholder:text-content-tertiary"
            />
            <button
              type="submit"
              disabled={asking || !question.trim()}
              className="mt-1.5 inline-flex items-center gap-1 rounded-md bg-oe-blue px-2.5 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
            >
              {asking ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />}
              Ask
            </button>
          </form>
          {askError ? <p className="mt-2 text-xs text-red-500">{askError}</p> : null}
          {askResult ? (
            <div className="mt-2 rounded-md border border-border/70 bg-surface-secondary p-2">
              <p className="whitespace-pre-wrap text-xs leading-relaxed text-content-primary">{askResult.answer}</p>
              {askResult.citations.length > 0 ? (
                <p className="mt-2 flex flex-wrap gap-1">
                  {askResult.citations.map((page) => (
                    <button
                      key={page}
                      type="button"
                      onClick={() => handleCitationClick(page)}
                      className="rounded-full bg-oe-blue px-2 py-0.5 text-[11px] font-bold text-white"
                    >
                      Page {page} →
                    </button>
                  ))}
                </p>
              ) : null}
              <p className="mt-1 text-[11px] text-content-tertiary">
                {askResult.provider} · {askResult.model}
              </p>
            </div>
          ) : null}
        </div>
      )}

      <p className="rounded-md border border-amber-200 bg-amber-50 p-2 text-[11px] leading-relaxed text-amber-800">
        AI answers are suggestions — verify on the drawing itself before takeoff. Nothing posts to estimation
        until you confirm.
      </p>

      {today ? (
        <div className="rounded-md border border-border/80 bg-surface-primary/80 p-3 shadow-sm">
          <p className="text-[10px] font-bold uppercase tracking-widest text-content-tertiary">
            Today · {today.date}
          </p>
          <p className="mt-1 text-xs text-content-secondary">
            {today.searches} searches · {today.asks} asks · {today.ocr_runs} OCR runs · {today.documents}{' '}
            documents
          </p>
          {Object.keys(today.by_provider).length > 0 ? (
            <p className="mt-1 text-xs text-content-secondary">
              Asks by provider:{' '}
              {Object.entries(today.by_provider)
                .map(([name, count]) => `${name} ${count}`)
                .join(' · ')}
            </p>
          ) : null}
          {today.recent.length > 0 ? (
            <ul className="mt-2 space-y-1">
              {today.recent.slice(0, 5).map((entry, index) => (
                <li key={index} className="text-[11px] leading-relaxed text-content-secondary">
                  <span className="font-semibold text-content-primary">{entry.time}</span> {entry.summary}
                  {entry.document_name ? (
                    <span className="text-content-tertiary"> - {entry.document_name}</span>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-1 text-[11px] text-content-tertiary">No AI Assistant activity yet today.</p>
          )}
        </div>
      ) : null}
    </div>
  );
}
