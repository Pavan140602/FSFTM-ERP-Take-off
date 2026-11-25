# OE-DELIVERY: 2026-11-02-auto-takeoff
"""AI assist and document plumbing for Auto Takeoff.

The geometry engine (``auto_takeoff``) works with no AI at all. When
the user turns "Use AI" on, their own saved provider key (Settings > AI,
same resolution as every other AI feature) is used for two things only:

1. **Reading labels the rules do not know.** The page's unknown short
   labels and its schedule / legend text are sent as TEXT; the model
   says what each label is (beam size, joist or truss mark, wall-type
   tag, or nothing) and lists wall-type descriptions. Geometry is still
   taken from the PDF's own lines.
2. **Scanned sheets.** A page with no text layer is rendered and the
   model reads the callouts and their positions off the image; lines
   come from the raster (OpenCV), so the same engine places markups.

Any AI failure degrades to the rules-only result with a plain message —
Auto Takeoff never fails because a key is missing or a call timed out.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import math
import re
import uuid
from typing import Any

from app.modules.takeoff import auto_takeoff as A
from app.modules.takeoff import detect as D

logger = logging.getLogger(__name__)

AI_PAGE_LIMIT = 12
AI_TIMEOUT = 75.0
AI_CONCURRENCY = 3

_SYSTEM_TEXT = (
    "You are a structural steel and cold-formed steel (CFS) quantity takeoff assistant. "
    "You read text found on a framing plan and say what each label names. Answer with "
    "JSON only, no prose."
)

_PROMPT_TEXT = """Framing sheet text (page {page}).

Schedules / legends / notes on or near this sheet:
---
{schedules}
---

Short labels found on the plan that the rules could not classify (text, times seen):
{labels}

For EACH label above decide what it names on a framing plan:
- "beams": a steel beam / girder / member size printed along a member line
- "columns": a column mark or size
- "joists": a joist mark or joist series (spacing like @ 24" O.C.)
- "trusses": a truss mark (T1, GT2, RT-1 ...) printed on a truss line
- "walls": a wall-type tag (W1, SW-4, A3 ...) defined by a wall / shear-wall schedule
- "other": headers, bracing, angles, purlins, straps
- "ignore": grid bubbles, section / detail / sheet references, dimensions, room names, notes

Return exactly this JSON:
{{"labels": [{{"text": "<label exactly as listed>", "category": "<one of the above>", "designation": "<member size or tag>", "spacing_in": <number or null>, "spec": "<short description from the schedules, or null>"}}],
 "wall_types": {{"<tag>": "<description from the wall schedule>"}},
 "column_marks": {{"<column mark, e.g. C1>": "<its profile from the column schedule, e.g. HSS8X8X1/2>"}}}}
Only list labels from the list above. Use "ignore" when unsure."""

_SYSTEM_VISION = (
    "You read scanned structural framing drawings. You list every framing callout you can "
    "read with its position. Answer with JSON only."
)

_PROMPT_VISION = """This is a scanned structural framing plan. List every framing callout text you can read:
member sizes (W12X26, HSS6X6X1/4, 600S162-54, 18K4), joist / truss series with spacing
(e.g. "1200S200-54 @ 4'-0\\" O.C."), truss marks (T1, GT2), wall-type tags (W1, SW-4), headers (HDR).
Skip dimensions, grid bubbles, notes, title block and schedules.

For each callout give its bounding box as fractions of the image (0..1, origin top-left)
and the reading direction of the text in degrees (0 = left-to-right horizontal,
90 = reading bottom-to-top, -90 = reading top-to-bottom).

Return exactly: {"labels": [{"text": "...", "box": [x0, y0, x1, y1], "angle": 0}]}"""


# ── credentials ───────────────────────────────────────────────────────


async def resolve_ai(session: Any, user_id: str) -> dict[str, Any]:
    """The user's saved AI provider, key and model, or a clear error."""
    try:
        from app.modules.ai.ai_client import resolve_provider_key_model
        from app.modules.ai.repository import AISettingsRepository

        settings = None
        if user_id:
            settings = await AISettingsRepository(session).get_by_user_id(uuid.UUID(str(user_id)))
        provider, api_key, model = resolve_provider_key_model(settings)
        return {"ok": True, "provider": provider, "api_key": api_key, "model": model}
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Auto Takeoff AI key resolution failed: %s", exc)
        return {"ok": False, "error": "Could not read your AI settings. Open Settings > AI and save your key."}


async def ai_status(session: Any, user_id: str) -> dict[str, Any]:
    creds = await resolve_ai(session, user_id)
    if not creds.get("ok"):
        return {"configured": False, "message": creds.get("error")}
    from app.modules.ai.ai_client import default_model_for

    return {
        "configured": True,
        "provider": creds["provider"],
        "model": creds.get("model") or default_model_for(creds["provider"]),
    }


async def _call(creds: dict[str, Any], system: str, prompt: str, image_b64: str | None = None, media: str = "image/png") -> Any:
    from app.modules.ai.ai_client import call_ai, extract_json

    text, _tokens = await call_ai(
        provider=creds["provider"],
        api_key=creds["api_key"],
        system=system,
        prompt=prompt,
        image_base64=image_b64,
        image_media_type=media,
        max_tokens=4096,
        model=creds.get("model"),
        timeout=AI_TIMEOUT,
    )
    return extract_json(text)


# ── text classification ───────────────────────────────────────────────


_VALID = set(A.CATEGORIES) | {"ignore"}


def parse_hints(data: Any) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    hints: dict[str, dict[str, Any]] = {}
    specs: dict[str, str] = {}
    if not isinstance(data, dict):
        return hints, specs
    for row in data.get("labels") or []:
        if not isinstance(row, dict):
            continue
        text = re.sub(r"\s+", "", str(row.get("text") or "").upper())
        cat = str(row.get("category") or "").strip().lower()
        if cat == "wall":
            cat = "walls"
        if not text or cat not in _VALID:
            continue
        spacing = row.get("spacing_in")
        try:
            spacing = float(spacing) if spacing not in (None, "") else None
        except (TypeError, ValueError):
            spacing = None
        if spacing is not None and not (4 <= spacing <= 144):
            spacing = None
        des = re.sub(r"\s+", "", str(row.get("designation") or text).upper())[:40] or text
        spec = row.get("spec")
        hints[text] = {
            "category": cat,
            "designation": des,
            "spacing_in": spacing,
            "spec": str(spec)[:160] if spec else None,
        }
    for tag, desc in (data.get("wall_types") or {}).items():
        t = re.sub(r"\s+", "", str(tag).upper())
        if t and desc:
            specs[t] = str(desc)[:160]
    # Column mark -> profile, kept in the same dict under a prefix so the
    # signature stays (OE-DELIVERY 2026-11-02-auto-takeoff-columns).
    for mark, prof in (data.get("column_marks") or {}).items():
        m = re.sub(r"\s+", "", str(mark).upper())
        profile = A._profile_in(str(prof or ""))
        if m and profile:
            specs[f"@COL:{m}"] = profile
    return hints, specs


async def classify_pages(creds: dict[str, Any], models: list[A.PageModel]) -> tuple[dict[int, dict[str, dict[str, Any]]], dict[str, str], list[str]]:
    sem = asyncio.Semaphore(AI_CONCURRENCY)
    hints_by_page: dict[int, dict[str, dict[str, Any]]] = {}
    specs: dict[str, str] = {}
    errors: list[str] = []

    async def one(model: A.PageModel) -> None:
        inventory = A.unknown_label_inventory(model)
        if not inventory:
            return
        labels = "\n".join(f"- {row['text']} (x{row['count']})" for row in inventory)
        prompt = _PROMPT_TEXT.format(page=model.page_no, schedules=A.schedule_text(model) or "(none on this sheet)", labels=labels)
        async with sem:
            try:
                data = await _call(creds, _SYSTEM_TEXT, prompt)
            except Exception as exc:
                errors.append(f"Page {model.page_no}: {str(exc)[:160]}")
                return
        hints, page_specs = parse_hints(data)
        if hints:
            hints_by_page[model.page_no] = hints
        for k, v in page_specs.items():
            specs.setdefault(k, v)

    await asyncio.gather(*(one(m) for m in models[:AI_PAGE_LIMIT]))
    return hints_by_page, specs, errors


# ── scanned sheets ────────────────────────────────────────────────────


def is_scanned(model: A.PageModel) -> bool:
    return len(model.labels) < 6 and len(model.segments) < 40


def raster_segments(page, dpi: int = 150) -> list[A.Seg]:
    """Straight lines of a scanned page (OpenCV), in PDF points."""
    try:
        import cv2
        import numpy as np
    except Exception:
        return []
    pix = page.get_pixmap(dpi=dpi, alpha=False, colorspace="gray")
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
    _thr, binary = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    lines = cv2.HoughLinesP(binary, 1, np.pi / 360, threshold=80, minLineLength=int(dpi * 0.4), maxLineGap=4)
    sx = float(page.rect.width) / pix.width
    sy = float(page.rect.height) / pix.height
    out: list[A.Seg] = []
    if lines is None:
        return out
    for x1, y1, x2, y2 in (ln[0] for ln in lines[:20000]):
        a = (x1 * sx, y1 * sy)
        b = (x2 * sx, y2 * sy)
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        if length >= 20:
            out.append((a[0], a[1], b[0], b[1], length, 1.0, (0, 0, 0)))
    return out


def page_png(page, long_edge_px: int = 2000) -> tuple[str, float, float]:
    zoom = long_edge_px / max(float(page.rect.width), float(page.rect.height))
    pix = page.get_pixmap(matrix=__import__("pymupdf").Matrix(zoom, zoom), alpha=False)
    return base64.b64encode(pix.tobytes("png")).decode("ascii"), float(page.rect.width), float(page.rect.height)


def labels_from_vision(data: Any, width: float, height: float) -> list[A.Label]:
    out: list[A.Label] = []
    if not isinstance(data, dict):
        return out
    for row in data.get("labels") or []:
        try:
            text = " ".join(str(row.get("text") or "").split())
            box = [float(v) for v in row.get("box")]
            angle = float(row.get("angle") or 0.0)
        except (TypeError, ValueError, AttributeError):
            continue
        if not text or len(box) != 4:
            continue
        x0, y0, x1, y1 = (max(0.0, min(1.0, v)) for v in box)
        rect = (min(x0, x1) * width, min(y0, y1) * height, max(x0, x1) * width, max(y0, y1) * height)
        # Vision angle is counter-clockwise on screen; ours is in y-down space.
        rad = math.radians(-angle)
        short = min(rect[2] - rect[0], rect[3] - rect[1])
        out.append(A.Label(text, rect, A._fold(-angle), max(short, 6.0), math.cos(rad), math.sin(rad)))
    return out


# ── document entry point ──────────────────────────────────────────────


_UNAVAILABLE = {
    "available": False,
    "message": (
        "This drawing is open as a local file, so the server cannot read it. "
        "Upload it to the project once - then Auto Takeoff can read it."
    ),
}


async def run_for_document(
    session: Any,
    doc: Any,
    user_id: str,
    *,
    pages: list[int] | None,
    categories: list[str],
    use_ai: bool,
    include_details: bool,
) -> dict[str, Any]:
    path = D._resolve_file(doc)
    if path is None:
        return dict(_UNAVAILABLE)
    import pymupdf

    def _load() -> tuple[list[A.PageModel], list[A.PageModel], int]:
        pdf = pymupdf.open(path)
        try:
            count = len(pdf)
            wanted = [p for p in (pages or list(range(1, count + 1))) if 1 <= p <= count][:150]
            models, spec_models = A.build_models(pdf, wanted, want_specs=True)
            return models, spec_models, count
        finally:
            pdf.close()

    models, spec_models, page_count = await asyncio.to_thread(_load)

    ai: dict[str, Any] = {"requested": use_ai, "used": False, "message": None, "pages": []}
    hints_by_page: dict[int, dict[str, dict[str, Any]]] = {}
    extra_specs: dict[str, str] = {}
    scanned = [m for m in models if is_scanned(m)]
    if use_ai:
        creds = await resolve_ai(session, user_id)
        if not creds.get("ok"):
            ai["message"] = creds.get("error")
        else:
            ai["provider"] = creds["provider"]
            errors: list[str] = []
            # Scanned pages: read callouts off the image, lines off the raster.
            if scanned:
                from app.modules.takeoff.plan_read import is_vision_capable

                if not is_vision_capable(creds["provider"], creds.get("model")):
                    errors.append("Your AI model cannot read images, so scanned pages were skipped.")
                else:
                    for model in scanned[:AI_PAGE_LIMIT]:
                        def _render(page_no: int = model.page_no):
                            pdf = pymupdf.open(path)
                            try:
                                pg = pdf[page_no - 1]
                                return page_png(pg), raster_segments(pg)
                            finally:
                                pdf.close()

                        (b64, w, h), segs = await asyncio.to_thread(_render)
                        try:
                            data = await _call(creds, _SYSTEM_VISION, _PROMPT_VISION, image_b64=b64)
                        except Exception as exc:
                            errors.append(f"Page {model.page_no}: {str(exc)[:160]}")
                            continue
                        model.labels = labels_from_vision(data, w, h)
                        model.segments = segs
                        model.index = A.SegIndex(segs)
                        ai["pages"].append(model.page_no)
            text_models = [m for m in models if m not in scanned]
            if text_models:
                hints_by_page, extra_specs, errs = await classify_pages(creds, text_models)
                errors.extend(errs)
                ai["pages"].extend(sorted(hints_by_page))
            ai["used"] = bool(ai["pages"])
            if errors:
                ai["message"] = " ".join(errors[:3])
    elif scanned:
        ai["message"] = (
            f"{len(scanned)} page(s) look scanned (no text layer). Turn on 'Use AI' with your API key to read them."
        )

    result = await asyncio.to_thread(
        A.run_models,
        models,
        spec_models,
        categories,
        hints_by_page=hints_by_page,
        include_details=include_details,
        extra_specs=extra_specs,
    )
    result["available"] = True
    result["page_count"] = page_count
    result["ai"] = ai
    result["document_id"] = str(getattr(doc, "id", ""))
    return result
