"""Who-is-working-where tracking for PDF Measurements."""

import time

from app.modules.takeoff import presence


def _p(user: str, doc: str, project: str = "proj-1", page: int = 1, at: float | None = None) -> presence.Presence:
    return presence.Presence(
        user_id=user,
        name=user.title(),
        email=f"{user}@example.com",
        document_id=doc,
        document_name=f"{doc}.pdf",
        project_id=project,
        page=page,
        at=time.time() if at is None else at,
    )


def setup_function() -> None:
    presence._reset_for_tests()


def test_reports_show_who_is_on_which_drawing_and_page() -> None:
    presence.report(_p("ana", "d1", page=3))
    presence.report(_p("ben", "d2", page=7))
    rows = presence.active("proj-1")
    assert {(r["user_id"], r["document_id"], r["page"]) for r in rows} == {("ana", "d1", 3), ("ben", "d2", 7)}


def test_latest_report_per_person_and_drawing_wins() -> None:
    presence.report(_p("ana", "d1", page=1))
    presence.report(_p("ana", "d1", page=5))
    rows = presence.active("proj-1")
    assert len(rows) == 1 and rows[0]["page"] == 5


def test_other_projects_are_filtered_and_stale_entries_expire() -> None:
    presence.report(_p("ana", "d1", project="proj-1"))
    presence.report(_p("cal", "d9", project="proj-2"))
    presence.report(_p("old", "d1", at=time.time() - presence.ACTIVE_FOR_S - 5))
    assert [r["user_id"] for r in presence.active("proj-1")] == ["ana"]
    assert {r["user_id"] for r in presence.active()} == {"ana", "cal"}


def test_leaving_removes_the_entry() -> None:
    presence.report(_p("ana", "d1"))
    presence.leave("ana", "d1")
    assert presence.active("proj-1") == []
