# OE-DELIVERY: 2026-10-22-register-role-invite (was 2026-10-14-transmittal-email-mockup-style-v1)
# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
# Copyright (c) 2026 Artem Boiko / DataDrivenConstruction
"""Shared HTML email templates.

Centralises the visual shell (logo, CSS, footer) and the per-event
templates (task-assigned, invoice-approved, safety-alert, meeting,
password-reset).  Each template returns ``(subject, html_body)`` so the
caller can decide whether to wrap it in an ``EmailMessage`` and push it
through the service, or inspect it directly in unit tests.

Kept template-only - no I/O, no settings, no side effects - so it can
be imported from tests without touching the rest of the stack.
"""

from __future__ import annotations

import html as _html
from functools import lru_cache

_LOGO_URL = "https://openconstructionerp.com/logo-128.png"
_APP_NAME = "OpenConstructionERP"


@lru_cache(maxsize=1)
def _base_style() -> str:
    return (
        "font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; "
        "line-height: 1.5; color: #1d1d1f; max-width: 560px; margin: 0 auto; padding: 24px;"
    )


def wrap(
    title: str,
    body: str,
    action_url: str | None = None,
    action_label: str = "View",
    *,
    footer: str | None = None,
) -> str:
    """Wrap *body* in the standard email shell (logo, title, CTA, footer).

    ``footer`` replaces the default English "notification preferences" line,
    which is wrong for mail nobody subscribed to, such as an invitation; an
    empty string leaves the footer out. It is inserted as given, so escape it.
    """
    btn = ""
    if action_url:
        btn = (
            f'<p style="margin-top:20px;">'
            f'<a href="{action_url}" style="display:inline-block; padding:10px 24px; '
            f"background:#0071e3; color:#fff; border-radius:8px; text-decoration:none; "
            f'font-weight:600;">{action_label}</a></p>'
        )
    return (
        f"<!DOCTYPE html><html><head><meta charset='utf-8'></head>"
        f'<body style="{_base_style()}">'
        f'<img src="{_LOGO_URL}" alt="{_APP_NAME}" width="40" height="40" '
        f'style="margin-bottom:12px;"/>'
        f"<h2 style='margin:0 0 12px;'>{title}</h2>"
        f"{body}"
        f"{btn}"
        f"{_footer_block(footer)}"
        f"</body></html>"
    )


def _footer_block(footer: str | None) -> str:
    if footer is None:
        footer = f"Sent by {_APP_NAME}. You received this because of your notification preferences."
    if not footer:
        return ""
    return (
        f"<hr style='border:none; border-top:1px solid #e5e5ea; margin:28px 0 12px;'/>"
        f"<p style='font-size:12px; color:#86868b;'>{footer}</p>"
    )


def template_task_assigned(
    task_title: str,
    assignee_name: str,
    project_name: str,
    action_url: str | None = None,
    assigner_name: str | None = None,
    assigner_role: str | None = None,
    due_date: str | None = None,
    description: str | None = None,
) -> tuple[str, str]:
    """Task-assignment email. Shows who assigned it and who owns it so the
    chain of responsibility is clear across roles (FSFTM workflow §3)."""
    subject = f"Task assigned: {task_title}"
    assigner_line = ""
    if assigner_name:
        role_part = f" ({assigner_role})" if assigner_role else ""
        assigner_line = (
            f"<p style='color:#555;'>Assigned by: "
            f"<strong>{assigner_name}</strong>{role_part}</p>"
        )
    due_line = f"<p>Due date: <strong>{due_date}</strong></p>" if due_date else ""
    desc_line = (
        f"<p style='color:#555;'>{description}</p>" if description else ""
    )
    body = (
        f"<p>Hi {assignee_name},</p>"
        f"{assigner_line}"
        f"<p>You've been assigned a task in <strong>{project_name}</strong>:</p>"
        f"<blockquote style='border-left:3px solid #0071e3; padding-left:12px; margin:12px 0;'>"
        f"{task_title}</blockquote>"
        f"{desc_line}"
        f"{due_line}"
    )
    return subject, wrap("Task Assigned", body, action_url, "Open Task")


def template_invoice_approved(
    invoice_number: str,
    amount: str,
    project_name: str,
    action_url: str | None = None,
) -> tuple[str, str]:
    subject = f"Invoice {invoice_number} approved"
    body = (
        f"<p>Invoice <strong>{invoice_number}</strong> for "
        f"<strong>{amount}</strong> in project <em>{project_name}</em> has been approved.</p>"
    )
    return subject, wrap("Invoice Approved", body, action_url, "View Invoice")


def template_safety_alert(
    description: str,
    reporter_name: str,
    project_name: str,
    action_url: str | None = None,
) -> tuple[str, str]:
    subject = f"Safety alert: {description[:60]}"
    body = (
        f"<p>A <strong style='color:#ff3b30;'>high-risk</strong> safety observation has "
        f"been reported in <em>{project_name}</em> by {reporter_name}:</p>"
        f"<blockquote style='border-left:3px solid #ff3b30; padding-left:12px; margin:12px 0;'>"
        f"{description}</blockquote>"
    )
    return subject, wrap("Safety Alert", body, action_url, "View Observation")


def template_meeting_invitation(
    meeting_title: str,
    meeting_date: str,
    location: str | None,
    project_name: str,
    action_url: str | None = None,
) -> tuple[str, str]:
    subject = f"Meeting: {meeting_title} on {meeting_date}"
    loc = f"<br/>Location: {location}" if location else ""
    body = (
        f"<p>A meeting has been scheduled in <em>{project_name}</em>:</p>"
        f"<p><strong>{meeting_title}</strong><br/>"
        f"Date: {meeting_date}{loc}</p>"
    )
    return subject, wrap("Meeting Scheduled", body, action_url, "View Meeting")


def template_transmittal_sent(
    transmittal_number: str,
    subject: str,
    documents: list[tuple[str, str | None]],
    *,
    project_name: str | None = None,
    sender_name: str | None = None,
    recipient_name: str | None = None,
    sent_date: str | None = None,
    action_url: str | None = None,
    pixel_url: str | None = None,
) -> tuple[str, str]:
    """Transmittal notification email — approved mockup style.

    Layout matches the mockup the user approved: CONSTRUCTION TRANSMITTAL
    badge, blue "Transmittal Received" banner, label/value Details table,
    blue "View Transmittal & Acknowledge" button, do-not-reply footer.
    All user-controlled values are HTML-escaped.

    Acknowledgement is button-only: the public view page's Acknowledge
    button. There is no inbound handler that turns an email reply into an
    ack, so the footer says "Do not reply" (the previous "reply to
    acknowledge" line promised a mechanism that did not exist).
    ``pixel_url`` (per-recipient tracking pixel) is appended as a 1x1
    image when given; clients that block images simply never load it.
    """
    email_subject = f"Transmittal {transmittal_number}: {subject}"

    label_style = (
        "padding:12px 16px; color:#555; vertical-align:top; width:140px; "
        "background:#f5f5f5;"
    )
    value_style = "padding:12px 16px; vertical-align:top;"

    def _row(label: str, value: str) -> str:
        return (
            f"<tr><td style='{label_style}'>{label}</td>"
            f"<td style='{value_style}'>{value}</td></tr>"
        )

    rows = [_row("Transmittal No:", _html.escape(transmittal_number))]
    if project_name:
        rows.append(_row("Project:", _html.escape(project_name)))
    if sent_date:
        rows.append(_row("Date:", _html.escape(sent_date)))
    if sender_name:
        rows.append(_row("From:", _html.escape(sender_name)))
    if documents:
        doc_items = "<br>".join(
            f"\U0001f4ce {_html.escape(name)}"
            + (f" ({_html.escape(version)})" if version else "")
            for name, version in documents
        )
        count = len(documents)
        docs_value = (
            f"{count} file{'s' if count != 1 else ''}<br>{doc_items}"
        )
        rows.append(_row("Documents:", docs_value))

    btn = ""
    if action_url:
        btn = (
            "<p style='text-align:center; margin:24px 0 8px;'>"
            f"<a href='{action_url}' style='display:inline-block; background:#1d63e8; "
            "color:#ffffff; font-size:17px; font-weight:700; padding:14px 32px; "
            "border-radius:8px; text-decoration:none;'>"
            "View Transmittal &amp; Acknowledge</a></p>"
        )
    html = (
        "<!DOCTYPE html><html><head><meta charset='utf-8'></head>"
        f"<body style='{_base_style()}'>"
        "<p style='margin:0 0 16px;'><span style='display:inline-block; "
        "border:1px solid #c7d7f5; border-radius:999px; padding:6px 14px; "
        "color:#1d4ed8; font-size:13px; font-weight:700; letter-spacing:0.5px;'>"
        "\U0001f3d7\ufe0f CONSTRUCTION TRANSMITTAL</span></p>"
        "<div style='background:#6e9be8; color:#1e3a8a; font-size:20px; "
        "font-weight:700; padding:12px 16px; border-radius:8px 8px 0 0;'>"
        "&#10003; Transmittal Received</div>"
        "<p style='font-size:17px; margin:16px 0 4px;'>"
        "You have received a transmittal from FSFTM</p>"
        "<p style='font-size:20px; font-weight:700; margin:0 0 12px;'>Details</p>"
        "<div style='background:#a9c3ec; height:6px; border-radius:4px 4px 0 0;'></div>"
        "<table style='border-collapse:collapse; width:100%; "
        "border:1px solid #d9d9d9; border-top:none; font-size:16px;'>"
        f"{''.join(rows)}"
        "</table>"
        f"{btn}"
        "<p style='text-align:center; font-size:15px; color:#333; margin:8px 0;'>"
        "Please acknowledge receipt by clicking the button above.</p>"
        "<p style='text-align:center; font-size:14px; color:#6e6e73; margin:0 0 24px;'>"
        "Sent by OpenConstructionERP</p>"
        "<div style='background:#f2f2f2; padding:12px 16px; font-size:12px; "
        "color:#6e6e73; border-radius:0 0 8px 8px;'>"
        "This is an automated message from FSFTM ERP. Do not reply to this email.</div>"
        "</body></html>"
    )
    if pixel_url:
        # 1x1 tracking pixel, per-recipient. Invisible; image-blocking
        # clients never load it (open tracking is best-effort).
        html = html.replace(
            "</body>",
            f'<img src="{pixel_url}" width="1" height="1" '
            f'style="display:none" alt="" /></body>',
        )
    return email_subject, html


def template_password_reset(
    recipient_name: str | None,
    reset_url: str,
    token_lifetime_minutes: int = 60,
) -> tuple[str, str]:
    """Password-reset template.

    ``reset_url`` already carries the token as a query parameter - the
    template does not embed the raw token separately so we never leak it
    to copy-paste or forwarded-email attack paths.
    """
    greeting = f"Hi {recipient_name}," if recipient_name else "Hello,"
    subject = "Reset your OpenConstructionERP password"
    body = (
        f"<p>{greeting}</p>"
        f"<p>We received a request to reset the password on your "
        f"<strong>{_APP_NAME}</strong> account. Click the button below to choose a new one. "
        f"The link is valid for {token_lifetime_minutes} minutes.</p>"
        f"<p style='font-size:13px; color:#6e6e73;'>If you did not request a password reset, "
        f"you can safely ignore this email - your password will not change.</p>"
    )
    return subject, wrap("Reset your password", body, reset_url, "Reset password")


def template_user_invite(
    recipient_name: str | None,
    register_url: str,
) -> tuple[str, str]:
    """User-invitation template: a plain registration link.

    Sent when an admin uses Users -> Invite User. No account is created
    and no token is embedded - the invitee follows the link, registers
    with their own password, picks their role on the form, and an
    administrator activates the account before they can sign in.
    """
    greeting = f"Hi {recipient_name}," if recipient_name else "Hello,"
    subject = f"You've been invited to {_APP_NAME}"
    body = (
        f"<p>{greeting}</p>"
        f"<p>You have been invited to join <strong>{_APP_NAME}</strong>. "
        f"Click the button below to create your account - you will set your "
        f"own password and choose your role during registration. An "
        f"administrator will then activate your account so you can sign in.</p>"
        f"<p style='font-size:13px; color:#6e6e73;'>If you were not expecting "
        f"this invitation, you can safely ignore this email.</p>"
    )
    return subject, wrap(
        "You're invited", body, register_url, "Create your account", footer=""
    )
