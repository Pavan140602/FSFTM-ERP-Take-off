"""Studio sessions - the pure helpers (OE-DELIVERY 2026-11-27-fsftm-pdf).

The database flow (invite, join, access granted and taken back, finish) was
checked against a scratch PostgreSQL database; these cover the parts that do
not need one.
"""

from app.modules.takeoff import studio


def test_session_code_is_readable_and_unique_enough() -> None:
    codes = {studio.new_code() for _ in range(200)}
    assert len(codes) > 190
    for c in codes:
        assert len(c) == 11 and c[3] == "-" and c[7] == "-" and c.replace("-", "").isdigit()


def test_code_accepts_spaces_and_no_dashes() -> None:
    assert studio.normalise_code("123456789") == "123-456-789"
    assert studio.normalise_code(" 123 456 789 ") == "123-456-789"
    assert studio.normalise_code("123-456-789") == "123-456-789"
    assert studio.normalise_code("12-34") == ""


def test_clean_emails_dedupes_and_drops_junk() -> None:
    assert studio.clean_emails(["A@x.com", "a@x.com ", "bad", "b@y", "c@z.org"]) == ["a@x.com", "c@z.org"]


def test_summarise_counts_per_person_type_and_pdf() -> None:
    rows = [
        {"created_by": "u1", "document_id": "d1", "type": "distance"},
        {"created_by": "u1", "document_id": "d2", "type": "area"},
        {"created_by": "u2", "document_id": "d1", "type": "distance"},
        {"created_by": "u1", "document_id": "d1", "type": "distance"},
    ]
    out = studio.summarise(rows, {"u1": {"name": "Ana", "email": "ana@x.com"}})
    assert out["total"] == 4
    first = out["people"][0]
    assert first["user_id"] == "u1" and first["name"] == "Ana" and first["count"] == 3
    assert first["by_type"] == {"distance": 2, "area": 1}
    d1 = next(d for d in out["documents"] if d["document_id"] == "d1")
    assert d1["count"] == 3 and d1["by_user"] == {"u1": 2, "u2": 1}


def test_folder_paths_are_cleaned_and_have_parents() -> None:
    assert studio.normalise_folder(" Drawings // Level 2 / ") == "Drawings/Level 2"
    assert studio.normalise_folder("../a/./b") == "a/b"
    assert studio.normalise_folder(r"a\b") == "a/b"
    assert studio.normalise_folder("/") == ""
    assert studio.with_parents("a/b/c") == ["a", "a/b", "a/b/c"]
    assert studio.with_parents("") == []
