# OE-DELIVERY: 2026-10-15-estimation-review-v1
# DDC-CWICR-OE: DataDrivenConstruction · OpenConstructionERP
"""Service for the estimation internal review workflow."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.projects.estimation_review import (
    EstimationReview,
    EstimationReviewSubmit,
    EstimationReviewResponse,
)
from app.modules.projects.models import Project, ProjectStatusHistory


async def submit_estimation_review(
    session: AsyncSession,
    project_id: uuid.UUID,
    submitted_by: uuid.UUID,
    data: EstimationReviewSubmit,
) -> EstimationReviewResponse:
    """Submit a project for internal review. Sends notifications to reviewers."""
    # Verify project exists and is in estimating stage
    project = (
        await session.execute(select(Project).where(Project.id == project_id))
    ).scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.status not in ("active", "estimation"):
        raise HTTPException(
            status_code=400,
            detail="Project must be in Estimating stage to submit for review",
        )

    # Check for existing pending review
    existing = (
        await session.execute(
            select(EstimationReview).where(
                EstimationReview.project_id == project_id,
                EstimationReview.status == "pending",
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Review already pending for this project")

    review = EstimationReview(
        project_id=project_id,
        submitted_by=submitted_by,
        status="pending",
        lead_estimator_id=data.lead_estimator_id,
        coordinator_id=data.coordinator_id,
        manager_id=data.manager_id,
        note=data.note,
    )
    session.add(review)
    await session.flush()

    # Send notifications to reviewers
    from app.modules.notifications.service import NotificationService

    notif_service = NotificationService(session)
    reviewers = [
        (data.lead_estimator_id, "Lead Estimator"),
        (data.coordinator_id, "Coordinator"),
        (data.manager_id, "Manager"),
    ]
    for reviewer_id, role_label in reviewers:
        if reviewer_id:
            try:
                await notif_service.create(
                    user_id=reviewer_id,
                    notification_type="estimation_review_requested",
                    title_key="Estimation review requested",
                    entity_type="project",
                    entity_id=str(project_id),
                    body_key=f"You have been asked to review the estimation for '{project.name}' as {role_label}.",
                    action_url=f"/projects/{project_id}",
                    metadata={"review_id": str(review.id), "role": role_label},
                )
            except Exception:
                pass  # Don't fail the submission if notification fails

    await session.commit()
    await session.refresh(review)
    return EstimationReviewResponse.model_validate(review)


async def approve_estimation_review(
    session: AsyncSession,
    project_id: uuid.UUID,
    approver_id: uuid.UUID,
) -> EstimationReviewResponse:
    """Manager approves the estimation review. Moves project to Estimation Submitted."""
    review = (
        await session.execute(
            select(EstimationReview).where(
                EstimationReview.project_id == project_id,
                EstimationReview.status == "pending",
            )
        )
    ).scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="No pending review for this project")

    # Only the designated manager can approve
    # OE-DELIVERY 2026-10-15: compare as strings — approver_id is str (JWT sub),
    # manager_id is UUID from DB. Direct UUID != str is always True!
    if str(review.manager_id) != str(approver_id):
        raise HTTPException(
            status_code=403, detail="Only the designated manager can approve this review"
        )

    review.status = "approved"
    review.manager_approved_at = datetime.now(timezone.utc)

    # Move project to Estimation Submitted
    # OE-DELIVERY 2026-10-15: move on manager approval regardless of the
    # exact current status — pre-existing projects may carry statuses
    # outside ('active', 'estimation'). Only skip if already past this stage.
    project = (
        await session.execute(select(Project).where(Project.id == project_id))
    ).scalar_one_or_none()
    if project and project.status not in (
        "estimation_submitted",
        "submitted_to_client",
        "awaiting_response",
        "won",
        "lost",
    ):
        old_status = project.status
        project.status = "estimation_submitted"
        # approver_id is str (JWT sub); changed_by needs UUID
        approver_uuid = uuid.UUID(str(approver_id))
        session.add(
            ProjectStatusHistory(
                project_id=project.id,
                from_status=old_status,
                to_status="estimation_submitted",
                changed_by=approver_uuid,
                note="Manager approved estimation review",
            )
        )

    # Notify the submitter
    from app.modules.notifications.service import NotificationService

    notif_service = NotificationService(session)
    try:
        await notif_service.create(
            user_id=review.submitted_by,
            notification_type="estimation_review_approved",
            title_key="Estimation review approved",
            entity_type="project",
            entity_id=str(project_id),
            body_key=f"The estimation for '{project.name}' has been approved by the manager.",
            action_url=f"/projects/{project_id}",
            metadata={"review_id": str(review.id)},
        )
    except Exception:
        pass

    await session.commit()
    await session.refresh(review)
    return EstimationReviewResponse.model_validate(review)


async def get_estimation_review(
    session: AsyncSession,
    project_id: uuid.UUID,
) -> EstimationReviewResponse | None:
    """Get the current (pending or latest) review for a project."""
    review = (
        await session.execute(
            select(EstimationReview)
            .where(EstimationReview.project_id == project_id)
            .order_by(EstimationReview.created_at.desc())
        )
    ).scalars().first()
    if not review:
        return None
    return EstimationReviewResponse.model_validate(review)
