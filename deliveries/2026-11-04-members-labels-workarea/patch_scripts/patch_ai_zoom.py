# OE-DELIVERY 2026-11-04-auto-takeoff-zoom: scanned sheets are read zoomed in (2x2 overlapping
# tiles) so small callouts are not missed; finer raster lines; report what was read first.
from pathlib import Path
import sys

ROOT = Path(sys.argv[1])


def patch(rel, pairs):
    p = ROOT / rel
    s = p.read_text(encoding='utf-8')
    for old, new in pairs:
        if s.count(old) != 1:
            print('ANCHOR FAIL', rel, s.count(old), old[:140])
            sys.exit(1)
        s = s.replace(old, new)
    p.write_text(s, encoding='utf-8')


patch('auto_takeoff_ai.py', [
    ('''def labels_from_vision(data: Any, width: float, height: float) -> list[A.Label]:''',
     '''def page_tiles_png(page, grid: int = 2, overlap: float = 0.08, long_edge_px: int = 2000) -> list[tuple[str, float, float, float, float]]:
    """The sheet cut into grid x grid overlapping tiles, each rendered zoomed
    in (OE-DELIVERY 2026-11-04-auto-takeoff-zoom). Returns (png, x0, y0, w, h)
    per tile in PDF points."""
    import pymupdf

    W, H = float(page.rect.width), float(page.rect.height)
    tw, th = W / grid, H / grid
    out: list[tuple[str, float, float, float, float]] = []
    for iy in range(grid):
        for ix in range(grid):
            x0 = max(0.0, ix * tw - overlap * tw)
            y0 = max(0.0, iy * th - overlap * th)
            x1 = min(W, (ix + 1) * tw + overlap * tw)
            y1 = min(H, (iy + 1) * th + overlap * th)
            clip = pymupdf.Rect(x0, y0, x1, y1)
            zoom = long_edge_px / max(x1 - x0, y1 - y0)
            pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=clip, alpha=False)
            out.append((base64.b64encode(pix.tobytes("png")).decode("ascii"), x0, y0, x1 - x0, y1 - y0))
    return out


def merge_tile_labels(parts: list[list[A.Label]]) -> list[A.Label]:
    """Labels from overlapping tiles, each callout kept once."""
    out: list[A.Label] = []
    for labels in parts:
        for lab in labels:
            if any(o.text == lab.text and abs(o.cx - lab.cx) < 8 and abs(o.cy - lab.cy) < 8 for o in out):
                continue
            out.append(lab)
    return out


def labels_from_vision(data: Any, width: float, height: float) -> list[A.Label]:'''),
    ('''                    for model in scanned[:AI_PAGE_LIMIT]:
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
                        model.labels = labels_from_vision(data, w, h)''',
     '''                    for model in scanned[:AI_PAGE_LIMIT]:
                        def _render(page_no: int = model.page_no):
                            pdf = pymupdf.open(path)
                            try:
                                pg = pdf[page_no - 1]
                                return page_tiles_png(pg), raster_segments(pg, dpi=220)
                            finally:
                                pdf.close()

                        tiles, segs = await asyncio.to_thread(_render)
                        # Read each zoomed-in quarter so small callouts are not missed.
                        parts: list[list[A.Label]] = []
                        failed = False
                        for b64, x0, y0, tw, th in tiles:
                            try:
                                data = await _call(creds, _SYSTEM_VISION, _PROMPT_VISION, image_b64=b64)
                            except Exception as exc:
                                errors.append(f"Page {model.page_no}: {str(exc)[:160]}")
                                failed = True
                                break
                            shifted = []
                            for lab in labels_from_vision(data, tw, th):
                                r = lab.rect
                                shifted.append(A.Label(lab.text, (r[0] + x0, r[1] + y0, r[2] + x0, r[3] + y0), lab.angle, lab.size, lab.ux, lab.uy))
                            parts.append(shifted)
                        if failed and not parts:
                            continue
                        model.labels = merge_tile_labels(parts)'''),
])

patch('auto_takeoff.py', [
    ('''    return {"pages": results, "specs": specs, "column_marks": col_marks}''',
     '''    # What was read before drawing (OE-DELIVERY 2026-11-04-auto-takeoff-zoom):
    # schedules, column marks and the sheets the notes came from.
    read = {
        "schedule_rows": len(specs),
        "wall_types": sum(1 for k in specs if _WALL_TAG_RE.match(k)),
        "header_jamb_types": sum(1 for k in specs if _HDR_TAG_RE.match(k) or _JAMB_TAG_RE.match(k)),
        "column_marks": len(col_marks),
        "sheets_read": len(spec_models),
    }
    return {"pages": results, "specs": specs, "column_marks": col_marks, "read": read}'''),
])
print('ok')
