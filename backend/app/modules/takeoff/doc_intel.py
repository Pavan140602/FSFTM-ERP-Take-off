# OE-DELIVERY: 2026-10-29-doc-intel-v2 (was 2026-10-28-doc-intel)
# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
"""Document intelligence for the PDF Measurements AI Assistant panel.

Reads the per-page text the takeoff upload flow already extracted
(``TakeoffDocument.page_data``) and adds three panel features on top of
it, without touching that upload pipeline:

* ``build_summary`` - per-page readable/scanned counts for the panel
  header. No new table: the summary is derived from the existing row.
* ``search_pages`` - keyword search across the document's page texts
  (embedded text first, OCR text as fallback) with a context snippet
  per match, so the panel can jump the viewer to the right page.
* ``ask_about_document`` - question answering over the matching pages
  through the user's own saved AI provider key (same key resolution as
  the Settings connection test). Answers cite the pages used as context;
  the model is instructed to say so when the answer is not in the text,
  never to invent sheet content.
* OCR for scanned pages - ``run_ocr_build`` renders text-less pages
  with PyMuPDF and OCRs them with Tesseract when both are installed.
  Results land in ``metadata_["doc_intel_ocr"]`` (a namespaced key, so
  the upload flow's ``page_data``/``analysis`` columns are never
  overwritten). When Tesseract is missing, ``ocr_available`` reports
  it plainly instead of failing the panel.
* Activity log - ``log_activity`` appends one row per panel action
  (search / ask / ocr) to ``oe_takeoff_doc_intel_activity`` and
  ``today_activity`` rolls the signed-in user's day up for the
  panel's Today card, so the estimator can review their daily work.
  Logging never raises: a failed log write must not break the
  search or answer the user actually asked for.

All helpers degrade gracefully: a missing library, an unreadable PDF
or an unparsable id returns an empty result or a clear error string,
never an unhandled exception to the caller.
"""

from __future__ import annotations

import logging
import math
import re
import uuid as _uuid
from datetime import datetime, time, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.database import async_session_factory
from app.modules.takeoff.models import TakeoffDocument

logger = logging.getLogger(__name__)

# Providers the panel may ask through - the same list the Settings
# connection test accepts, so the panel can never name a provider the
# AI module does not know.
VALID_PROVIDERS = (
    "anthropic",
    "openai",
    "gemini",
    "openrouter",
    "mistral",
    "groq",
    "deepseek",
    "together",
    "fireworks",
    "perplexity",
    "cohere",
    "ai21",
    "xai",
    "zhipu",
    "baidu",
    "yandex",
    "gigachat",
    "ollama",
    "kimi",
    "vllm",
)

SELF_HOSTED_PROVIDERS = ("ollama", "vllm")

MAX_MATCHES = 50
MAX_SNIPPET_CHARS = 400
MAX_CONTEXT_PAGES = 6
MAX_CONTEXT_CHARS_PER_PAGE = 1500
ASK_TIMEOUT = 60.0
ASK_MAX_TOKENS = 1024

# OCR caps mirror the file_search extractor: a large-format sheet at
# 150 DPI can otherwise allocate hundreds of MB per page render, and a
# 1000-page scan must not pin an OCR worker.
OCR_DPI = 150
OCR_MAX_PIXELS = 40_000_000
OCR_MAX_PAGES = 200

_STOPWORDS = frozenset(
    "a an the and or of to in on for with is are was were be by at from "
    "what where which show me find list give tell how many all any".split()
)


# ── Page texts ─────────────────────────────────────────────────────────


def embedded_page_texts(doc: Any) -> list[dict[str, Any]]:
    """Per-page embedded texts from the upload flow's ``page_data``."""
    pages: list[dict[str, Any]] = []
    for entry in (getattr(doc, "page_data", None) or []):
        try:
            page = int(entry.get("page"))
        except (TypeError, ValueError):
            continue
        text = entry.get("text") or ""
        pages.append({"page": page, "text": text, "has_text": bool(text.strip())})
    pages.sort(key=lambda p: p["page"])
    return pages


def ocr_page_texts(doc: Any) -> dict[int, str]:
    """Per-page OCR texts previously stored under ``metadata_``."""
    meta = getattr(doc, "metadata_", None) or {}
    ocr = meta.get("doc_intel_ocr") or {}
    out: dict[int, str] = {}
    for key, value in (ocr.get("pages") or {}).items():
        try:
            out[int(key)] = value or ""
        except (TypeError, ValueError):
            continue
    return out


def merged_page_texts(doc: Any) -> dict[int, str]:
    """Page -> searchable text: embedded text wins, OCR fills the gaps."""
    merged: dict[int, str] = {}
    for page in embedded_page_texts(doc):
        merged[page["page"]] = page["text"]
    for page, text in ocr_page_texts(doc).items():
        if not (merged.get(page) or "").strip() and (text or "").strip():
            merged[page] = text
    return merged


def build_summary(doc: Any) -> dict[str, Any]:
    """Panel header data for one document."""
    embedded = embedded_page_texts(doc)
    ocr = ocr_page_texts(doc)
    total = getattr(doc, "pages", 0) or 0
    if not total and embedded:
        total = max(p["page"] for p in embedded)
    rows: list[dict[str, Any]] = []
    readable = 0
    scanned = 0
    for page in embedded:
        has = page["has_text"] or bool((ocr.get(page["page"]) or "").strip())
        if has:
            readable += 1
        else:
            scanned += 1
        rows.append(
            {
                "page": page["page"],
                "has_text": has,
                "chars": len(page["text"]),
                "ocr": bool((ocr.get(page["page"]) or "").strip()),
            }
        )
    ocr_built = sum(1 for text in ocr.values() if (text or "").strip())
    return {
        "document_id": str(getattr(doc, "id", "")),
        "filename": getattr(doc, "filename", ""),
        "index_available": bool(embedded),
        "page_count": total,
        "readable_pages": readable,
        "scanned_pages": scanned,
        "pages": rows,
        "ocr": {
            "built_pages": ocr_built,
            "status": (getattr(doc, "metadata_", None) or {}).get("doc_intel_ocr", {}).get("status"),
        },
    }


# ── Search ─────────────────────────────────────────────────────────────


def _snippet(text: str, match_at: int, match_len: int) -> str:
    """~120 chars of context around a match, cut on whitespace."""
    start = max(0, match_at - 80)
    end = min(len(text), match_at + match_len + 120)
    chunk = re.sub(r"\s+", " ", text[start:end]).strip()
    if len(chunk) > MAX_SNIPPET_CHARS:
        chunk = chunk[:MAX_SNIPPET_CHARS].rstrip() + "..."
        return chunk
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(text) else ""
    return prefix + chunk + suffix


def search_pages(doc: Any, query: str) -> list[dict[str, Any]]:
    """Case-insensitive keyword search across the document's pages."""
    needle = (query or "").strip().lower()
    if not needle:
        return []
    matches: list[dict[str, Any]] = []
    for page in sorted(merged_page_texts(doc)):
        text = merged_page_texts(doc)[page]
        at = text.lower().find(needle)
        if at < 0:
            continue
        matches.append(
            {"page": page, "snippet": _snippet(text, at, len(needle))}
        )
        if len(matches) >= MAX_MATCHES:
            break
    return matches


def _question_words(question: str) -> list[str]:
    """Significant words from a question, for context retrieval."""
    words: list[str] = []
    for word in re.findall(r"[A-Za-z0-9][A-Za-z0-9\-/]*", question or ""):
        lowered = word.lower()
        if len(lowered) >= 3 and lowered not in _STOPWORDS and lowered not in words:
            words.append(lowered)
    return words


# ── OCR ────────────────────────────────────────────────────────────────


def ocr_available() -> tuple[bool, str]:
    """Whether Tesseract OCR can run on this server."""
    try:
        import pytesseract

        pytesseract.get_tesseract_version()
        return True, ""
    except ImportError:
        return (
            False,
            "pytesseract is not installed on the server. Install it with "
            "pip install pytesseract and install the Tesseract binary, "
            "then retry.",
        )
    except Exception:
        return (
            False,
            "The Tesseract binary was not found on the server. Install "
            "Tesseract OCR, then retry.",
        )


def _clamp_render_scale(width_pt: float, height_pt: float, dpi: int, max_pixels: int) -> float:
    """Raster scale for ``dpi`` that never exceeds ``max_pixels``."""
    scale = dpi / 72.0
    if width_pt <= 0 or height_pt <= 0:
        return scale
    est_pixels = int(width_pt * scale) * int(height_pt * scale)
    if est_pixels > max_pixels:
        scale = math.sqrt(max_pixels / (width_pt * height_pt))
    return scale


def _resolve_doc_file(doc: Any) -> Path | None:
    """Resolve a takeoff document's PDF bytes, mirroring the download route."""
    from app.core.storage import is_within_safe_root
    from app.modules.takeoff.service import _find_existing_takeoff_pdf

    doc_id = str(getattr(doc, "id", ""))
    file_path = _find_existing_takeoff_pdf(doc_id)
    if file_path is None and getattr(doc, "file_path", None):
        try:
            candidate = Path(doc.file_path).resolve()
        except OSError:
            candidate = None
        if candidate is not None and candidate.is_file() and not candidate.is_symlink():
            file_path = candidate
    if file_path is None:
        return None
    try:
        if not is_within_safe_root(file_path):
            return None
    except Exception:
        return None
    if not file_path.exists() or file_path.is_symlink():
        return None
    return file_path


async def run_ocr_build(doc_id: str) -> None:
    """Background OCR pass: fills text-less pages, stores them in metadata_.

    Runs on its own session (the request session is gone by the time a
    background task runs). A server restart mid-run leaves the previous
    metadata_ untouched, so the panel can simply offer Rebuild.
    """
    try:
        import fitz
        from PIL import Image
        import pytesseract
    except Exception:
        logger.warning("OCR build skipped: PyMuPDF/Pillow/pytesseract missing")
        return
    try:
        doc_uuid = _uuid.UUID(doc_id)
    except (ValueError, TypeError):
        return
    try:
        async with async_session_factory() as session:
            result = await session.execute(
                select(TakeoffDocument).where(TakeoffDocument.id == doc_uuid)
            )
            doc = result.scalar_one_or_none()
            if doc is None:
                return
            path = _resolve_doc_file(doc)
            if path is None:
                meta = dict(doc.metadata_ or {})
                meta["doc_intel_ocr"] = {"status": "failed", "error": "PDF file not found on disk", "pages": {}}
                doc.metadata_ = meta
                await session.commit()
                return
            payload = path.read_bytes()
            existing = {p["page"]: p["text"] for p in embedded_page_texts(doc)}
            ocr_pages: dict[str, str] = {}
            with fitz.open(stream=payload, filetype="pdf") as pdf:
                for index, page in enumerate(pdf):
                    number = index + 1
                    if (existing.get(number) or "").strip():
                        continue
                    if len(ocr_pages) >= OCR_MAX_PAGES:
                        break
                    try:
                        scale = _clamp_render_scale(
                            page.rect.width, page.rect.height, OCR_DPI, OCR_MAX_PIXELS
                        )
                        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                        with Image.open(BytesIO(pix.tobytes("png"))) as img:
                            ocr_pages[str(number)] = pytesseract.image_to_string(img) or ""
                    except Exception:
                        logger.exception("OCR failed for page %s; continuing", number)
                        continue
            meta = dict(doc.metadata_ or {})
            meta["doc_intel_ocr"] = {
                "status": "ready",
                "engine": "pytesseract",
                "pages": ocr_pages,
            }
            doc.metadata_ = meta
            await session.commit()
    except Exception:
        logger.exception("OCR build failed for document %s", doc_id)


# ── Activity log (daily work tracking) ─────────────────────────────


def _as_uuid(value: Any) -> Any:
    """Best-effort UUID coercion for log-row id columns."""
    if value is None or isinstance(value, _uuid.UUID):
        return value
    try:
        return _uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None


async def log_activity(
    session: Any,
    user_id: str,
    doc: Any,
    action: str,
    detail: dict[str, Any],
) -> None:
    """Append one AI Assistant activity row. Never raises.

    The log is a convenience for the estimator's own daily review; a
    failed write (table missing on an unpatched backend, DB hiccup)
    must never break the search/answer the user actually asked for.
    """
    try:
        if session is None:
            return
        uid = _as_uuid(user_id)
        if uid is None:
            return
        from app.modules.takeoff.models import DocIntelActivity

        session.add(
            DocIntelActivity(
                user_id=uid,
                document_id=_as_uuid(getattr(doc, "id", None)),
                project_id=_as_uuid(getattr(doc, "project_id", None)),
                document_name=(getattr(doc, "filename", "") or "")[:500],
                action=action,
                detail=detail or {},
            )
        )
        await session.commit()
    except Exception:
        logger.exception("doc-intel activity log failed")
        try:
            await session.rollback()
        except Exception:
            pass


async def today_activity(session: Any, user_id: str) -> dict[str, Any]:
    """Today's AI Assistant activity for one user (the Today card).

    "Today" is the server's local calendar day: created_at is stored
    in UTC, so the local-midnight boundary is converted to UTC for the
    query and row times are converted back to local for display.
    """
    from app.modules.takeoff.models import DocIntelActivity

    empty: dict[str, Any] = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "searches": 0,
        "asks": 0,
        "ocr_runs": 0,
        "documents": 0,
        "by_provider": {},
        "recent": [],
    }
    if session is None:
        return empty
    uid = _as_uuid(user_id)
    if uid is None:
        return empty
    local_midnight = datetime.combine(datetime.now().date(), time.min)
    start_utc = local_midnight.astimezone(timezone.utc)
    try:
        result = await session.execute(
            select(DocIntelActivity)
            .where(
                DocIntelActivity.user_id == uid,
                DocIntelActivity.created_at >= start_utc,
            )
            .order_by(DocIntelActivity.created_at.desc())
        )
        rows = list(result.scalars().all())
    except Exception:
        logger.exception("doc-intel activity read failed")
        return empty

    by_provider: dict[str, int] = {}
    for row in rows:
        if row.action != "ask":
            continue
        provider = (row.detail or {}).get("provider") or "unknown"
        by_provider[provider] = by_provider.get(provider, 0) + 1

    recent: list[dict[str, Any]] = []
    for row in rows[:10]:
        ts = row.created_at
        if ts is not None and ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        detail = row.detail or {}
        if row.action == "search":
            summary = f"Search '{detail.get('query', '')}' - {detail.get('matches', 0)} matches"
        elif row.action == "ask":
            summary = f"Ask ({detail.get('provider', '')}): {detail.get('question', '')}"
        elif row.action == "ocr":
            summary = "OCR started for scanned pages"
        else:
            summary = row.action
        recent.append(
            {
                "time": ts.astimezone().strftime("%H:%M") if ts else "",
                "action": row.action,
                "document_name": row.document_name or "",
                "summary": summary[:160],
            }
        )

    return {
        "date": empty["date"],
        "searches": sum(1 for row in rows if row.action == "search"),
        "asks": sum(1 for row in rows if row.action == "ask"),
        "ocr_runs": sum(1 for row in rows if row.action == "ocr"),
        "documents": len({str(row.document_id) for row in rows if row.document_id}),
        "by_provider": by_provider,
        "recent": recent,
    }


# ── Ask AI ─────────────────────────────────────────────────────────────


async def ask_about_document(
    doc: Any,
    provider: str,
    question: str,
    user_id: str,
    session: Any,
) -> dict[str, Any]:
    """Answer a question from the document's own page texts.

    Raises ValueError with a user-facing message when the provider has
    no usable key, so the router can return it instead of a traceback.
    """
    provider = (provider or "").strip()
    if provider not in VALID_PROVIDERS:
        raise ValueError(f"Unknown provider: {provider}.")
    if not (question or "").strip():
        raise ValueError("Question is required.")

    # Key + model resolution mirrors the Settings connection test.
    from app.core.crypto import decrypt_secret
    from app.modules.ai.ai_client import _model_override_for, call_ai, default_model_for
    from app.modules.ai.repository import AISettingsRepository

    settings = await AISettingsRepository(session).get_by_user_id(_uuid.UUID(user_id))
    self_hosted = provider in SELF_HOSTED_PROVIDERS
    key_attr = f"{provider}_api_key"
    raw = getattr(settings, key_attr, None) if settings else None
    if not raw and not self_hosted:
        raise ValueError(
            f"No API key configured for {provider}. Save it in Settings > AI first."
        )
    api_key = ""
    if raw:
        try:
            api_key = decrypt_secret(raw) or ""
        except Exception:
            api_key = ""
    if raw and not api_key:
        raise ValueError(
            "Stored key could not be decrypted - the backend encryption key "
            "has rotated since the key was saved. Please re-enter and save it in Settings."
        )
    saved_meta = (settings.metadata_ if settings else None) or {}
    resolved_url: str | None = None
    if provider in SELF_HOSTED_PROVIDERS and isinstance(saved_meta, dict):
        raw_url = saved_meta.get(f"{provider}_base_url")
        if isinstance(raw_url, str) and raw_url.strip():
            normalized = raw_url.strip().rstrip("/")
            if not normalized.endswith("/v1/chat/completions"):
                normalized += "/v1/chat/completions"
            resolved_url = normalized
    model_override = _model_override_for(settings, provider)
    effective_model = model_override or default_model_for(provider)

    # Context: pages matching the question's significant words first,
    # falling back to the first pages that have text at all.
    merged = merged_page_texts(doc)
    words = _question_words(question)
    ranked: list[int] = []
    for word in words:
        for page in sorted(merged):
            if page in ranked:
                continue
            if word in (merged[page] or "").lower():
                ranked.append(page)
            if len(ranked) >= MAX_CONTEXT_PAGES:
                break
        if len(ranked) >= MAX_CONTEXT_PAGES:
            break
    if not ranked:
        for page in sorted(merged):
            if (merged[page] or "").strip():
                ranked.append(page)
            if len(ranked) >= 3:
                break
    context_parts: list[str] = []
    for page in ranked:
        text = (merged.get(page) or "").strip()
        if not text:
            continue
        context_parts.append(f"[Page {page}]\n{text[:MAX_CONTEXT_CHARS_PER_PAGE]}")
    context = "\n\n".join(context_parts)

    system = (
        "You are a drawing assistant for a cold-formed steel estimator. "
        "Answer ONLY from the sheet text below. If the answer is not in "
        "the text, say so plainly instead of guessing. Cite the page "
        "numbers you used, like [Page 12]. Keep the answer short."
    )
    prompt = f"Sheet text:\n{context}\n\nQuestion: {question.strip()}"
    answer, _tokens = await call_ai(
        provider=provider,
        api_key=api_key,
        system=system,
        prompt=prompt,
        max_tokens=ASK_MAX_TOKENS,
        base_url=resolved_url,
        model=model_override,
        timeout=ASK_TIMEOUT,
    )
    return {
        "answer": answer,
        "citations": ranked,
        "model": effective_model,
        "provider": provider,
    }
