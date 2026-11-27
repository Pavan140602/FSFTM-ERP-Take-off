"""Who is working on which drawing (OE-DELIVERY 2026-11-27-fsftm-pdf).

Each open PDF Measurements viewer reports its drawing and page every few
seconds; a lead sees who is on which project, drawing and page, and when
they were last active. Kept in memory (the app runs as one server process):
an entry expires once its viewer stops reporting, and a restart simply starts
empty - nothing here is a record of work, only "who is here now".
"""

from __future__ import annotations

import threading
import time
from dataclasses import asdict, dataclass

#: Seconds after the last report that a person still counts as present.
ACTIVE_FOR_S = 90


@dataclass
class Presence:
    user_id: str
    name: str
    email: str
    document_id: str
    document_name: str
    project_id: str
    page: int
    at: float


_lock = threading.Lock()
_entries: dict[tuple[str, str], Presence] = {}


def report(p: Presence) -> None:
    """Record that ``p.user_id`` has ``p.document_id`` open now."""
    with _lock:
        _entries[(p.user_id, p.document_id)] = p
        _prune_locked(time.time())


def leave(user_id: str, document_id: str) -> None:
    """The viewer closed this drawing."""
    with _lock:
        _entries.pop((user_id, document_id), None)


def active(project_id: str | None = None) -> list[dict]:
    """Everyone active in the last ``ACTIVE_FOR_S`` seconds (newest first)."""
    now = time.time()
    with _lock:
        _prune_locked(now)
        rows = [e for e in _entries.values() if not project_id or e.project_id == project_id]
    rows.sort(key=lambda e: e.at, reverse=True)
    return [{**asdict(e), "seconds_ago": int(now - e.at)} for e in rows]


def _prune_locked(now: float) -> None:
    for key in [k for k, e in _entries.items() if now - e.at > ACTIVE_FOR_S]:
        del _entries[key]


def _reset_for_tests() -> None:
    with _lock:
        _entries.clear()
