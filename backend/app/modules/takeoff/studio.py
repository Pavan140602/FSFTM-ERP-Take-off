"""FSFTM Studio sessions (OE-DELIVERY 2026-11-27-fsftm-pdf).

A host starts a session, puts PDFs in it (from any of their projects) and
invites people by email. Everyone who joins marks up the same PDFs at the same
time - the viewer's live sync shows each person's markups to the others within
seconds - and can chat in the session. The host finishes the session at the
end and gets a report of who marked up what.

Access: the PDFs keep their normal project access rules. A person who joins
and is not on a PDF's project is added to that project's team for as long as
the session runs; the projects added this way are remembered on the attendee
(``granted``) and taken away again when they leave, are removed, or the host
finishes the session. Nobody keeps access they only had through a session.

Only invited people may join, unless the host lets anyone with the session ID
join (``open_join``).
"""

from __future__ import annotations

import html
import logging
import secrets
import uuid
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.takeoff import presence
from app.modules.takeoff.models import (
    StudioAttendee,
    StudioMessage,
    StudioSession,
    StudioSessionDocument,
    TakeoffDocument,
    TakeoffMeasurement,
)

logger = logging.getLogger(__name__)

#: How many chat lines one request returns at most.
MESSAGES_PAGE = 200


def new_code() -> str:
    """A session ID people can read out: ``123-456-789``."""
    n = f"{secrets.randbelow(10**9):09d}"
    return f"{n[:3]}-{n[3:6]}-{n[6:]}"


def normalise_code(code: str) -> str:
    """Accept ``123456789``, ``123 456 789`` or ``123-456-789``."""
    digits = "".join(ch for ch in code if ch.isdigit())
    if len(digits) != 9:
        return ""
    return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"


def clean_emails(raw: list[str]) -> list[str]:
    """Lower-cased, de-duplicated, plausible addresses (order kept)."""
    out: list[str] = []
    for e in raw:
        e = (e or "").strip().lower()
        if e and "@" in e and "." in e.split("@", 1)[1] and e not in out:
            out.append(e)
    return out


def normalise_folder(path: str) -> str:
    """``" a//b /c "`` -> ``"a/b/c"``; no ``..``, at most 8 levels of 80 chars."""
    parts = [p.strip()[:80] for p in (path or "").replace("\\", "/").split("/")]
    parts = [p for p in parts if p and p not in {".", ".."}]
    return "/".join(parts[:8])


def with_parents(path: str) -> list[str]:
    """``"a/b/c"`` -> ``["a", "a/b", "a/b/c"]``."""
    parts = path.split("/") if path else []
    return ["/".join(parts[: i + 1]) for i in range(len(parts))]


def summarise(rows: list[dict[str, Any]], names: dict[str, dict[str, str]]) -> dict[str, Any]:
    """Who marked up what: per person and per PDF, with counts by markup type.

    ``rows`` carry ``created_by``, ``document_id``, ``type``; ``names`` maps a
    user id to ``{"name", "email"}``. Pure, so it is unit tested directly.
    """
    people: dict[str, dict[str, Any]] = {}
    docs: dict[str, dict[str, Any]] = {}
    for r in rows:
        uid = r.get("created_by") or ""
        did = r.get("document_id") or ""
        kind = r.get("type") or "other"
        p = people.setdefault(
            uid,
            {
                "user_id": uid,
                "name": names.get(uid, {}).get("name", "") if uid else "",
                "email": names.get(uid, {}).get("email", "") if uid else "",
                "count": 0,
                "by_type": defaultdict(int),
            },
        )
        p["count"] += 1
        p["by_type"][kind] += 1
        d = docs.setdefault(did, {"document_id": did, "count": 0, "by_user": defaultdict(int)})
        d["count"] += 1
        d["by_user"][uid] += 1
    people_out = sorted(people.values(), key=lambda p: -p["count"])
    for p in people_out:
        p["by_type"] = dict(p["by_type"])
    docs_out = list(docs.values())
    for d in docs_out:
        d["by_user"] = dict(d["by_user"])
    return {"total": len(rows), "people": people_out, "documents": docs_out}


# ── Loading ─────────────────────────────────────────────────────────────────


async def load_for_user(db: AsyncSession, session_id: str, user_id: str) -> tuple[StudioSession, StudioAttendee]:
    """The session and the caller's own attendee row, or 404.

    404 (not 403) when the caller is not in it, like the rest of the takeoff
    API, so session ids cannot be probed.
    """
    try:
        sid = uuid.UUID(str(session_id))
        uid = uuid.UUID(str(user_id))
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail="Session not found") from None
    s = await db.get(StudioSession, sid)
    if s is None:
        raise HTTPException(status_code=404, detail="Session not found")
    att = (
        await db.execute(select(StudioAttendee).where(StudioAttendee.session_id == sid, StudioAttendee.user_id == uid))
    ).scalar_one_or_none()
    if att is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return s, att


def require_host(att: StudioAttendee) -> None:
    if att.role != "host":
        raise HTTPException(status_code=403, detail="Only the session host can do that")


def require_active(s: StudioSession) -> None:
    if s.status != "active":
        raise HTTPException(status_code=409, detail="This session has finished")


async def document_ids(db: AsyncSession, s: StudioSession) -> list[str]:
    rows = (
        await db.execute(
            select(StudioSessionDocument.document_id)
            .where(StudioSessionDocument.session_id == s.id)
            .order_by(StudioSessionDocument.created_at)
        )
    ).scalars()
    return list(rows)


async def _documents(db: AsyncSession, ids: list[str]) -> list[TakeoffDocument]:
    uuids = []
    for i in ids:
        try:
            uuids.append(uuid.UUID(i))
        except (ValueError, TypeError):
            continue
    if not uuids:
        return []
    rows = (await db.execute(select(TakeoffDocument).where(TakeoffDocument.id.in_(uuids)))).scalars()
    by_id = {str(d.id): d for d in rows}
    return [by_id[i] for i in ids if i in by_id]


async def _users(db: AsyncSession, ids: list[uuid.UUID]) -> dict[str, dict[str, str]]:
    from app.modules.users.models import User

    if not ids:
        return {}
    rows = (await db.execute(select(User.id, User.full_name, User.email).where(User.id.in_(ids)))).all()
    return {str(r.id): {"name": (r.full_name or "").strip(), "email": r.email} for r in rows}


# ── Project access for attendees ────────────────────────────────────────────


async def _has_project_access(db: AsyncSession, project_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    from app.dependencies import verify_project_access

    try:
        await verify_project_access(project_id, str(user_id), db)
        return True
    except HTTPException:
        return False


async def grant_access(
    db: AsyncSession, att: StudioAttendee, docs: list[TakeoffDocument], extra_projects: list[Any] | None = None
) -> None:
    """Put a joined attendee on every session PDF's project (and the session's
    own project, where its uploads go) that they are not on."""
    from app.modules.projects.member_schemas import AddProjectMemberRequest
    from app.modules.projects.member_service import add_project_member

    if att.user_id is None:
        return
    granted = list(att.granted or [])
    pids = [getattr(d, "project_id", None) for d in docs] + list(extra_projects or [])
    for pid in dict.fromkeys(str(p) for p in pids if p):
        try:
            puid = uuid.UUID(str(pid))
        except (ValueError, TypeError):
            continue
        if str(puid) in granted or await _has_project_access(db, puid, att.user_id):
            continue
        try:
            await add_project_member(db, puid, AddProjectMemberRequest(user_id=att.user_id, role="member"))
            granted.append(str(puid))
        except HTTPException as exc:
            logger.info("studio: could not add %s to project %s: %s", att.user_id, puid, exc.detail)
    att.granted = granted


async def revoke_access(db: AsyncSession, att: StudioAttendee, keep: set[str] | None = None) -> None:
    """Take back the project memberships this session gave (except ``keep``)."""
    from app.modules.projects.member_service import remove_project_member

    if att.user_id is None:
        return
    left: list[str] = []
    for pid in att.granted or []:
        if keep and pid in keep:
            left.append(pid)
            continue
        try:
            await remove_project_member(db, uuid.UUID(pid), att.user_id)
        except (HTTPException, ValueError, TypeError):
            pass  # already gone, or they became the owner meanwhile
    att.granted = left


async def _still_needed(db: AsyncSession, att: StudioAttendee) -> set[str]:
    """Projects the person still needs for OTHER active sessions they are in."""
    if att.user_id is None:
        return set()
    rows = (
        await db.execute(
            select(StudioAttendee)
            .join(StudioSession, StudioSession.id == StudioAttendee.session_id)
            .where(
                StudioAttendee.user_id == att.user_id,
                StudioAttendee.id != att.id,
                StudioAttendee.status == "joined",
                StudioSession.status == "active",
            )
        )
    ).scalars()
    keep: set[str] = set()
    for other in rows:
        keep.update(other.granted or [])
    return keep


# ── Actions ─────────────────────────────────────────────────────────────────


async def create(
    db: AsyncSession,
    *,
    host_id: str,
    host_email: str,
    name: str,
    docs: list[TakeoffDocument],
    open_join: bool,
    project_id: uuid.UUID | None = None,
) -> StudioSession:
    s = None
    for _ in range(8):
        code = new_code()
        clash = (await db.execute(select(StudioSession.id).where(StudioSession.code == code))).first()
        if clash is None:
            s = StudioSession(
                name=name.strip() or "Session",
                code=code,
                owner_id=uuid.UUID(host_id),
                open_join=open_join,
                project_id=project_id or (docs[0].project_id if docs else None),
                folders=[],
            )
            break
    if s is None:  # pragma: no cover - 1e9 codes
        raise HTTPException(status_code=500, detail="Could not make a session ID, try again")
    db.add(s)
    await db.flush()
    for d in docs:
        db.add(StudioSessionDocument(session_id=s.id, document_id=str(d.id), added_by=uuid.UUID(host_id)))
    db.add(
        StudioAttendee(
            session_id=s.id,
            user_id=uuid.UUID(host_id),
            email=host_email.lower(),
            role="host",
            status="joined",
            joined_at=datetime.now(UTC),
            granted=[],
        )
    )
    await db.flush()
    return s


async def invite(
    db: AsyncSession,
    s: StudioSession,
    inviter_id: str,
    emails: list[str],
    *,
    inviter_is_admin: bool,
    frontend_url: str,
) -> list[dict[str, str]]:
    """Invite people by email. Returns one result per address.

    ``invited``  - has an account: in-app notification + email with the link.
    ``emailed``  - no account yet, the inviter is an admin: a sign-up link was
                   emailed; they can join once an admin activates the account.
    ``no_account`` - no account and the inviter cannot create one.
    ``already``  - already in the session.
    """
    from app.modules.notifications.service import NotificationService
    from app.modules.users.models import User

    require_active(s)
    inviter = await _users(db, [uuid.UUID(inviter_id)])
    inviter_name = inviter.get(inviter_id, {}).get("name") or inviter.get(inviter_id, {}).get("email") or "Someone"
    results: list[dict[str, str]] = []
    for email in clean_emails(emails):
        existing = (
            await db.execute(
                select(StudioAttendee).where(StudioAttendee.session_id == s.id, StudioAttendee.email == email)
            )
        ).scalar_one_or_none()
        user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if existing is not None and existing.status != "left":
            results.append({"email": email, "status": "already"})
            continue
        if user is None or not user.is_active:
            if user is None and inviter_is_admin:
                from app.modules.users.service import _send_invite_link_email

                await _send_invite_link_email(email, f"{frontend_url}/register", email.split("@", 1)[0])
                if existing is None:
                    db.add(StudioAttendee(session_id=s.id, user_id=None, email=email, status="invited", granted=[]))
                results.append({"email": email, "status": "emailed"})
            else:
                results.append({"email": email, "status": "no_account"})
            continue
        if existing is None:
            db.add(StudioAttendee(session_id=s.id, user_id=user.id, email=email, status="invited", granted=[]))
        else:
            existing.user_id = user.id
            existing.status = "invited"
        link = f"/takeoff?tab=measurements&studio={s.id}"
        try:
            await NotificationService(db).create(
                user.id,
                "studio_invite",
                "notifications.takeoff.studio_invite.title",
                entity_type="takeoff_studio_session",
                entity_id=str(s.id),
                body_key="notifications.takeoff.studio_invite.body",
                body_context={"inviter": inviter_name, "session": s.name, "code": s.code},
                action_url=link,
            )
        except Exception:
            logger.exception("studio: invite notification for %s failed", email)
        await _email_invite(email, inviter_name, s, f"{frontend_url}{link}")
        results.append({"email": email, "status": "invited"})
    await db.flush()
    return results


async def _email_invite(to: str, inviter: str, s: StudioSession, url: str) -> None:
    """Best-effort email with the session link; never raises."""
    try:
        from app.core.email.base import EmailMessage
        from app.core.email.service import get_email_service

        body = (
            f"<p>{html.escape(inviter)} invited you to the session "
            f"<b>{html.escape(s.name)}</b> in PDF Measurements.</p>"
            f'<p><a href="{html.escape(url)}">Open the session</a></p>'
            f"<p>Or open PDF Measurements, choose Studio, Join, and enter the session ID "
            f"<b>{html.escape(s.code)}</b>.</p>"
        )
        await get_email_service().send(
            EmailMessage(to=to, subject=f"Session invite: {s.name}", html_body=body, tags=["studio_invite"])
        )
    except Exception:
        logger.exception("studio: invite email to %s failed", to)


async def join(db: AsyncSession, s: StudioSession, user_id: str, email: str) -> StudioAttendee:
    """Join (or re-join) a session; gives access to its PDFs."""
    require_active(s)
    uid = uuid.UUID(user_id)
    email = email.lower()
    att = (
        (
            await db.execute(
                select(StudioAttendee).where(
                    StudioAttendee.session_id == s.id,
                    (StudioAttendee.user_id == uid) | (StudioAttendee.email == email),
                )
            )
        )
        .scalars()
        .first()
    )
    if att is None:
        if not s.open_join:
            raise HTTPException(
                status_code=403, detail="You have not been invited to this session. Ask the host to invite you."
            )
        att = StudioAttendee(session_id=s.id, user_id=uid, email=email, status="joined", granted=[])
        db.add(att)
    att.user_id = uid
    att.status = "joined"
    att.joined_at = datetime.now(UTC)
    await grant_access(db, att, await _documents(db, await document_ids(db, s)), [s.project_id])
    await db.flush()
    return att


async def leave(db: AsyncSession, att: StudioAttendee) -> None:
    att.status = "left"
    await revoke_access(db, att, keep=await _still_needed(db, att))
    await db.flush()


async def remove_attendee(db: AsyncSession, s: StudioSession, attendee_id: str) -> None:
    try:
        aid = uuid.UUID(attendee_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail="Attendee not found") from None
    att = await db.get(StudioAttendee, aid)
    if att is None or att.session_id != s.id:
        raise HTTPException(status_code=404, detail="Attendee not found")
    if att.role == "host":
        raise HTTPException(status_code=400, detail="The host cannot be removed")
    await revoke_access(db, att, keep=await _still_needed(db, att))
    await db.delete(att)
    await db.flush()


async def add_documents(
    db: AsyncSession, s: StudioSession, user_id: str, docs: list[TakeoffDocument], folder: str = ""
) -> None:
    require_active(s)
    folder = normalise_folder(folder)
    if folder:
        _add_folder_paths(s, folder)
    have = set(await document_ids(db, s))
    new = [d for d in docs if str(d.id) not in have]
    for d in new:
        db.add(
            StudioSessionDocument(session_id=s.id, document_id=str(d.id), added_by=uuid.UUID(user_id), folder=folder)
        )
    if s.project_id is None and new:
        s.project_id = new[0].project_id
    await db.flush()
    if new:
        joined = (
            await db.execute(
                select(StudioAttendee).where(StudioAttendee.session_id == s.id, StudioAttendee.status == "joined")
            )
        ).scalars()
        for att in joined:
            await grant_access(db, att, new)
        await db.flush()


def _add_folder_paths(s: StudioSession, folder: str) -> None:
    have = list(s.folders or [])
    for p in with_parents(folder):
        if p not in have:
            have.append(p)
    s.folders = sorted(have, key=str.lower)


async def ensure_project(db: AsyncSession, s: StudioSession) -> bool:
    """Give the session's project-less PDFs a project.

    A PDF uploaded with no project selected is visible to its owner only and
    its markups are kept in that browser only - nobody else in the session
    could open it or see the markups. Such PDFs go into the session's
    project (created as "Studio - <session name>", owned by the host, when
    the session has none yet), and everyone who has joined gets access.
    Returns True when anything changed.
    """
    from app.modules.projects.models import Project

    docs = await _documents(db, await document_ids(db, s))
    loose = [d for d in docs if not getattr(d, "project_id", None)]
    if not loose and s.project_id is not None:
        return False
    if s.project_id is None:
        firsts = [d.project_id for d in docs if getattr(d, "project_id", None)]
        if firsts:
            s.project_id = firsts[0]
        else:
            p = Project(name=f"Studio - {s.name}"[:255], owner_id=s.owner_id)
            db.add(p)
            await db.flush()
            s.project_id = p.id
    for d in loose:
        d.project_id = s.project_id
    await db.flush()
    joined = (
        await db.execute(
            select(StudioAttendee).where(StudioAttendee.session_id == s.id, StudioAttendee.status == "joined")
        )
    ).scalars()
    for att in joined:
        await grant_access(db, att, docs, [s.project_id])
    await db.flush()
    return True


async def add_folder(db: AsyncSession, s: StudioSession, path: str) -> str:
    require_active(s)
    folder = normalise_folder(path)
    if not folder:
        raise HTTPException(status_code=400, detail="Give the folder a name")
    _add_folder_paths(s, folder)
    await db.flush()
    return folder


async def delete_folder(db: AsyncSession, s: StudioSession, path: str) -> None:
    """Remove an empty folder (and its empty sub-folders)."""
    require_active(s)
    folder = normalise_folder(path)
    rows = (await db.execute(select(StudioSessionDocument).where(StudioSessionDocument.session_id == s.id))).scalars()
    if any(r.folder == folder or r.folder.startswith(folder + "/") for r in rows):
        raise HTTPException(status_code=409, detail="The folder has PDFs in it - move or remove them first")
    s.folders = [f for f in (s.folders or []) if f != folder and not f.startswith(folder + "/")]
    await db.flush()


async def move_document(db: AsyncSession, s: StudioSession, document_id: str, path: str) -> None:
    require_active(s)
    row = (
        await db.execute(
            select(StudioSessionDocument).where(
                StudioSessionDocument.session_id == s.id, StudioSessionDocument.document_id == document_id
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="That PDF is not in the session")
    row.folder = normalise_folder(path)
    if row.folder:
        _add_folder_paths(s, row.folder)
    await db.flush()


async def remove_document(db: AsyncSession, s: StudioSession, document_id: str) -> None:
    row = (
        await db.execute(
            select(StudioSessionDocument).where(
                StudioSessionDocument.session_id == s.id, StudioSessionDocument.document_id == document_id
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="That PDF is not in the session")
    await db.delete(row)
    await db.flush()


async def finish(db: AsyncSession, s: StudioSession) -> None:
    """End the session for everyone and take back session-only access."""
    require_active(s)
    s.status = "finished"
    s.finished_at = datetime.now(UTC)
    await db.flush()
    atts = (await db.execute(select(StudioAttendee).where(StudioAttendee.session_id == s.id))).scalars().all()
    for att in atts:
        if att.status == "joined":
            att.status = "left"
        await revoke_access(db, att, keep=await _still_needed(db, att))
    await db.flush()


async def post_message(
    db: AsyncSession, s: StudioSession, user_id: str, text: str, mentions: list[str] | None = None
) -> StudioMessage:
    require_active(s)
    text = text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty message")
    m = StudioMessage(session_id=s.id, user_id=uuid.UUID(user_id), text=text[:4000])
    db.add(m)
    await db.flush()
    if mentions:
        await _notify_mentions(db, s, user_id, text, mentions)
    return m


async def _notify_mentions(db: AsyncSession, s: StudioSession, user_id: str, text: str, mentions: list[str]) -> None:
    """In-app notification for each @mentioned account (best effort)."""
    from app.modules.notifications.service import NotificationService

    me = await _users(db, [uuid.UUID(user_id)])
    who = me.get(user_id, {}).get("name") or me.get(user_id, {}).get("email") or "Someone"
    for mid in dict.fromkeys(mentions):
        try:
            uid = uuid.UUID(mid)
        except (ValueError, TypeError):
            continue
        if str(uid) == user_id:
            continue
        try:
            await NotificationService(db).create(
                uid,
                "studio_invite",
                "notifications.takeoff.studio_mention.title",
                entity_type="takeoff_studio_session",
                entity_id=str(s.id),
                body_key="notifications.takeoff.studio_mention.body",
                body_context={"who": who, "session": s.name, "excerpt": text[:140]},
                action_url=f"/takeoff?tab=measurements&studio={s.id}",
            )
        except Exception:
            logger.exception("studio: mention notification failed")


async def messages(db: AsyncSession, s: StudioSession) -> list[dict[str, Any]]:
    rows = list(
        (
            await db.execute(
                select(StudioMessage)
                .where(StudioMessage.session_id == s.id)
                .order_by(StudioMessage.created_at.desc())
                .limit(MESSAGES_PAGE)
            )
        ).scalars()
    )
    rows.reverse()
    names = await _users(db, list({m.user_id for m in rows}))
    return [
        {
            "id": str(m.id),
            "user_id": str(m.user_id),
            "name": names.get(str(m.user_id), {}).get("name") or names.get(str(m.user_id), {}).get("email", ""),
            "text": m.text,
            "at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in rows
    ]


# ── Read models ─────────────────────────────────────────────────────────────


async def detail(db: AsyncSession, s: StudioSession, me: StudioAttendee) -> dict[str, Any]:
    ids = await document_ids(db, s)
    docs = await _documents(db, ids)
    atts = list(
        (
            await db.execute(
                select(StudioAttendee).where(StudioAttendee.session_id == s.id).order_by(StudioAttendee.created_at)
            )
        ).scalars()
    )
    names = await _users(db, [a.user_id for a in atts if a.user_id])
    online: dict[str, dict[str, Any]] = {}
    doc_set = set(ids)
    for e in presence.active():
        if e["document_id"] in doc_set and e["user_id"] not in online:
            online[e["user_id"]] = e
    project_names = await _project_names(
        db, [d.project_id for d in docs if getattr(d, "project_id", None)] + ([s.project_id] if s.project_id else [])
    )
    rows = (await db.execute(select(StudioSessionDocument).where(StudioSessionDocument.session_id == s.id))).scalars()
    folder_of = {r.document_id: r.folder or "" for r in rows}
    return {
        "id": str(s.id),
        "name": s.name,
        "code": s.code,
        "status": s.status,
        "open_join": bool(s.open_join),
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "finished_at": s.finished_at.isoformat() if s.finished_at else None,
        "me": {"attendee_id": str(me.id), "role": me.role, "status": me.status},
        "project_id": str(s.project_id) if s.project_id else None,
        "project_name": project_names.get(str(s.project_id), "") if s.project_id else "",
        "folders": list(s.folders or []),
        "documents": [
            {
                "id": str(d.id),
                "name": d.filename,
                "pages": getattr(d, "pages", None),
                "project_id": str(d.project_id) if getattr(d, "project_id", None) else None,
                "project_name": project_names.get(str(d.project_id), "") if getattr(d, "project_id", None) else "",
                "folder": folder_of.get(str(d.id), ""),
            }
            for d in docs
        ],
        "attendees": [
            {
                "id": str(a.id),
                "user_id": str(a.user_id) if a.user_id else None,
                "name": names.get(str(a.user_id), {}).get("name", "") if a.user_id else "",
                "email": a.email,
                "role": a.role,
                "status": a.status,
                "online": bool(a.user_id and str(a.user_id) in online and a.status == "joined"),
                "document_id": online.get(str(a.user_id), {}).get("document_id") if a.user_id else None,
                "page": online.get(str(a.user_id), {}).get("page") if a.user_id else None,
            }
            for a in atts
        ],
    }


async def _project_names(db: AsyncSession, ids: list[Any]) -> dict[str, str]:
    from app.modules.projects.models import Project

    uuids = []
    for i in ids:
        try:
            uuids.append(uuid.UUID(str(i)))
        except (ValueError, TypeError):
            continue
    if not uuids:
        return {}
    rows = (await db.execute(select(Project.id, Project.name).where(Project.id.in_(uuids)))).all()
    return {str(r.id): r.name for r in rows}


async def my_sessions(db: AsyncSession, user_id: str) -> list[dict[str, Any]]:
    uid = uuid.UUID(user_id)
    rows = (
        await db.execute(
            select(StudioSession, StudioAttendee)
            .join(StudioAttendee, StudioAttendee.session_id == StudioSession.id)
            .where(StudioAttendee.user_id == uid)
            .order_by(StudioSession.created_at.desc())
            .limit(100)
        )
    ).all()
    out = []
    for s, a in rows:
        out.append(
            {
                "id": str(s.id),
                "name": s.name,
                "code": s.code,
                "status": s.status,
                "role": a.role,
                "my_status": a.status,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
        )
    return out


async def report(db: AsyncSession, s: StudioSession) -> dict[str, Any]:
    ids = await document_ids(db, s)
    docs = await _documents(db, ids)
    if not ids:
        return {"total": 0, "people": [], "documents": [], "since": None}
    rows = (
        await db.execute(
            select(TakeoffMeasurement.created_by, TakeoffMeasurement.document_id, TakeoffMeasurement.type).where(
                TakeoffMeasurement.document_id.in_(ids), TakeoffMeasurement.created_at >= s.created_at
            )
        )
    ).all()
    data = [{"created_by": r.created_by, "document_id": r.document_id, "type": r.type} for r in rows]
    uids = []
    for r in data:
        try:
            uids.append(uuid.UUID(r["created_by"]))
        except (ValueError, TypeError):
            continue
    out = summarise(data, await _users(db, list(set(uids))))
    names = {str(d.id): d.filename for d in docs}
    for d in out["documents"]:
        d["name"] = names.get(d["document_id"], "")
    out["since"] = s.created_at.isoformat() if s.created_at else None
    return out
