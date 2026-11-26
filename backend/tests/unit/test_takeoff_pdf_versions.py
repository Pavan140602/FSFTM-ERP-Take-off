"""Edited drawings are stored as numbered versions (FSFTM page tools).

Windows cannot replace a PDF that another reader still has open, so
``replace_document_file`` writes ``{doc_id}.v{n}.pdf`` instead of overwriting
``{doc_id}.pdf``; the lookup must always pick the newest version.
"""

from pathlib import Path

from app.modules.takeoff import service


def test_version_number_parsing() -> None:
    doc = "aef23a75-4f02-417f-ae13-92c24895ef64"
    assert service._pdf_version_of(Path(f"{doc}.v3.pdf"), doc) == 3
    assert service._pdf_version_of(Path(f"{doc}.pdf"), doc) is None
    assert service._pdf_version_of(Path(f"{doc}.v3.pdf.tmp"), doc) is None
    assert service._pdf_version_of(Path("other.v3.pdf"), doc) is None


def test_latest_version_wins(tmp_path: Path) -> None:
    doc = "d1"
    (tmp_path / f"{doc}.pdf").write_bytes(b"%PDF-orig")
    assert service._latest_pdf_version(tmp_path, doc) is None
    for n in (2, 10, 3):
        (tmp_path / f"{doc}.v{n}.pdf").write_bytes(b"%PDF-v")
    (tmp_path / "d10.v99.pdf").write_bytes(b"%PDF-other-doc")
    latest = service._latest_pdf_version(tmp_path, doc)
    assert latest is not None and latest.name == "d1.v10.pdf"


def test_find_existing_prefers_newest_version(tmp_path: Path, monkeypatch) -> None:
    doc = "d2"
    monkeypatch.setattr(service, "_takeoff_documents_dir", lambda: tmp_path)
    (tmp_path / f"{doc}.pdf").write_bytes(b"%PDF-orig")
    assert service._find_existing_takeoff_pdf(doc) == (tmp_path / f"{doc}.pdf").resolve()
    (tmp_path / f"{doc}.v2.pdf").write_bytes(b"%PDF-edit")
    assert service._find_existing_takeoff_pdf(doc) == tmp_path / f"{doc}.v2.pdf"
