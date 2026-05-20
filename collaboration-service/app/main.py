from __future__ import annotations

from collections import Counter
from typing import Any
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException

from shared.designvcs_common import (
    ApprovalDecision,
    ApprovalRecord,
    ApprovalRequest,
    CommentCreateRequest,
    CommentRecord,
    Role,
    Settings,
    detect_mentions,
    has_permission,
)

settings = Settings(service_name="collaboration-service", service_port=8423)
app = FastAPI(title="DesignVCS Collaboration Service", version="1.0.0")

comments_by_version: dict[str, list[CommentRecord]] = {}
approvals_by_version: dict[str, list[ApprovalRecord]] = {}


def _assert_permission(role: Role, action: str) -> None:
    if not has_permission(role, action):
        raise HTTPException(status_code=403, detail=f"Role {role.value} cannot perform {action}")


async def _notify_comment(version_id: str, comment_id: str, author_id: str) -> None:
    async with httpx.AsyncClient(timeout=8.0) as client:
        try:
            await client.post(
                f"{settings.notification_service_url}/notify/comment",
                json={
                    "version_id": version_id,
                    "comment_id": comment_id,
                    "author_id": author_id,
                    "recipients": ["project_reviewers"],
                },
                params={"actor_role": Role.ADMIN.value},
            )
        except httpx.HTTPError:
            return


async def _notify_mentions(version_id: str, comment_id: str, author_id: str, mentions: list[str]) -> None:
    if not mentions:
        return
    async with httpx.AsyncClient(timeout=8.0) as client:
        for user in mentions:
            try:
                await client.post(
                    f"{settings.notification_service_url}/notify/mention",
                    json={
                        "version_id": version_id,
                        "comment_id": comment_id,
                        "mentioned_user": user,
                        "author_id": author_id,
                    },
                    params={"actor_role": Role.ADMIN.value},
                )
            except httpx.HTTPError:
                continue


async def _notify_approval(version_id: str, reviewer_id: str, decision: str) -> None:
    async with httpx.AsyncClient(timeout=8.0) as client:
        try:
            await client.post(
                f"{settings.notification_service_url}/notify/approval",
                json={
                    "version_id": version_id,
                    "reviewer_id": reviewer_id,
                    "decision": decision,
                    "recipients": ["project_designers"],
                },
                params={"actor_role": Role.ADMIN.value},
            )
        except httpx.HTTPError:
            return


def _approval_summary(version_id: str) -> dict[str, Any]:
    approvals = approvals_by_version.get(version_id, [])
    counter = Counter(item.decision.value for item in approvals)
    final = ApprovalDecision.PENDING
    if counter[ApprovalDecision.REJECTED.value] > 0:
        final = ApprovalDecision.REJECTED
    elif counter[ApprovalDecision.CHANGES_REQUESTED.value] > 0:
        final = ApprovalDecision.CHANGES_REQUESTED
    elif approvals and all(item.decision == ApprovalDecision.APPROVED for item in approvals):
        final = ApprovalDecision.APPROVED

    return {
        "status": final.value,
        "approved": counter[ApprovalDecision.APPROVED.value],
        "changes_requested": counter[ApprovalDecision.CHANGES_REQUESTED.value],
        "rejected": counter[ApprovalDecision.REJECTED.value],
        "pending": counter[ApprovalDecision.PENDING.value],
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/versions/{version_id}/comments")
async def add_comment(
    version_id: str,
    request: CommentCreateRequest,
    actor_role: Role = Role.DESIGNER,
) -> dict[str, Any]:
    _assert_permission(actor_role, "collab:comment")

    mention_list = list(request.mentions)
    for username in detect_mentions(request.body):
        if username not in mention_list:
            mention_list.append(username)

    comment = CommentRecord(
        comment_id=str(uuid4()),
        version_id=version_id,
        author_id=request.author_id,
        body=request.body,
        mentions=mention_list,
        anchor_x=request.anchor_x,
        anchor_y=request.anchor_y,
    )
    comments_by_version.setdefault(version_id, []).append(comment)

    await _notify_comment(version_id, comment.comment_id, comment.author_id)
    await _notify_mentions(version_id, comment.comment_id, comment.author_id, mention_list)
    return comment.model_dump(mode="json")


@app.get("/versions/{version_id}/comments")
async def list_comments(version_id: str) -> dict[str, Any]:
    items = comments_by_version.get(version_id, [])
    payload = [item.model_dump(mode="json") for item in items]
    return {"items": payload, "count": len(payload)}


@app.post("/versions/{version_id}/approvals")
async def set_approval(version_id: str, request: ApprovalRequest, actor_role: Role = Role.REVIEWER) -> dict[str, Any]:
    _assert_permission(actor_role, "collab:approve")
    approvals = approvals_by_version.setdefault(version_id, [])

    existing = next((item for item in approvals if item.reviewer_id == request.reviewer_id), None)
    if existing is None:
        existing = ApprovalRecord(
            approval_id=str(uuid4()),
            version_id=version_id,
            reviewer_id=request.reviewer_id,
            decision=request.decision,
            notes=request.notes,
        )
        approvals.append(existing)
    else:
        existing.decision = request.decision
        existing.notes = request.notes

    await _notify_approval(version_id, request.reviewer_id, request.decision.value)
    return {
        "approval": existing.model_dump(mode="json"),
        "summary": _approval_summary(version_id),
    }


@app.get("/versions/{version_id}/approvals")
async def list_approvals(version_id: str) -> dict[str, Any]:
    approvals = approvals_by_version.get(version_id, [])
    payload = [item.model_dump(mode="json") for item in approvals]
    return {
        "items": payload,
        "count": len(payload),
        "summary": _approval_summary(version_id),
    }
