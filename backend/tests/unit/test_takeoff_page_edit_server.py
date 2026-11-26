"""Server-side page edits (FSFTM fast page tools).

``TakeoffService.edit_document_pages`` moves / rotates / deletes / inserts
pages with PyMuPDF and stores the result as a new numbered version, so the
viewer only sends the change instead of re-uploading the whole drawing.
"""

import asyncio
import uuid
from pathlib import Path
from types import SimpleNamespace

import pymupdf
import pytest

from app.modules.takeoff import service as svc


def _make_pdf(path: Path) -> None:
    pdf = pymupdf.open()
    for w, h in [(792, 612), (612, 792), (500, 500)]:
        pdf.new_page(width=w, height=h)
    pdf.save(str(path))
    pdf.close()


def _sizes(path: Path) -> list[tuple[int, int]]:
    with pymupdf.open(str(path)) as pdf:
        return [(round(p.rect.width), round(p.rect.height)) for p in pdf]


class _Session:
    async def flush(self) -> None:
        return None


def _service(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[svc.TakeoffService, SimpleNamespace]:
    doc_id = uuid.uuid4()
    _make_pdf(tmp_path / f"{doc_id}.pdf")
    doc = SimpleNamespace(
        id=doc_id, file_path=str(tmp_path / f"{doc_id}.pdf"), metadata_={}, pages=3, size_bytes=0, filename="t.pdf"
    )
    monkeypatch.setattr(svc, "_takeoff_documents_dir", lambda: tmp_path)
    monkeypatch.setattr(svc, "_schedule_full_parse", lambda *a, **k: None)
    service = svc.TakeoffService.__new__(svc.TakeoffService)

    async def _get(_id: object) -> SimpleNamespace:
        return doc

    service.repo = SimpleNamespace(get_by_id=_get)
    service.session = _Session()
    return service, doc


def test_reorder_rotate_insert_delete(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service, doc = _service(tmp_path, monkeypatch)
    run = lambda edit: asyncio.run(service.edit_document_pages(str(doc.id), edit))  # noqa: E731

    run({"kind": "reorder", "order": [3, 1, 2]})
    assert Path(doc.file_path).name == f"{doc.id}.v2.pdf"
    assert _sizes(Path(doc.file_path)) == [(500, 500), (792, 612), (612, 792)]
    assert doc.metadata_["tables_pending"] is True

    run({"kind": "rotate", "pages": [2], "deg": 90})
    assert _sizes(Path(doc.file_path))[1] == (612, 792)  # turned landscape -> portrait

    run({"kind": "insertBlank", "after": 2, "count": 1})
    sizes = _sizes(Path(doc.file_path))
    assert len(sizes) == 4 and sizes[2] == (612, 792)  # same as the page it follows, as shown
    assert doc.pages == 4

    run({"kind": "delete", "pages": [1]})
    assert doc.pages == 3
    assert svc._find_existing_takeoff_pdf(str(doc.id)) == Path(doc.file_path)


def test_rejects_bad_edits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service, doc = _service(tmp_path, monkeypatch)
    for bad in (
        {"kind": "reorder", "order": [1, 1, 2]},
        {"kind": "delete", "pages": [1, 2, 3]},
        {"kind": "rotate", "pages": [1], "deg": 45},
        {"kind": "nope"},
    ):
        with pytest.raises(svc.HTTPException):
            asyncio.run(service.edit_document_pages(str(doc.id), bad))


def test_page_thumbnail_is_rendered_and_cached(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(svc, "_takeoff_documents_dir", lambda: tmp_path)
    src = tmp_path / "doc.pdf"
    _make_pdf(src)
    out = svc.render_page_thumbnail(src, "doc", 1, 320)
    assert out is not None and out.read_bytes()[:3] == b"\xff\xd8\xff"  # JPEG
    assert pymupdf.Pixmap(str(out)).width == 320
    assert svc.render_page_thumbnail(src, "doc", 1, 320) == out  # cached
    assert svc.render_page_thumbnail(src, "doc", 9, 320) is None  # no such page
    _make_pdf(src)  # rewritten file -> new cache entry
    src.touch()
    assert svc.render_page_thumbnail(src, "doc", 1, 320) is not None
