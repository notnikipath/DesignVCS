from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from shared.designvcs_common import (
    NotificationEvent,
    NotificationRequest,
    NotificationType,
    Role,
    Settings,
    has_permission,
)

settings = Settings(service_name="notification-service", service_port=8426)
app = FastAPI(title="DesignVCS Notification Service", version="1.0.0")

notifications: list[NotificationEvent] = []


class VersionUploadedNotice(BaseModel):
    project_id: str
    version_id: str
    author_id: str
    recipients: list[str] = Field(default_factory=list)


class CommentNotice(BaseModel):
    version_id: str
    comment_id: str
    author_id: str
    recipients: list[str] = Field(default_factory=list)


class MentionNotice(BaseModel):
    version_id: str
    comment_id: str
    mentioned_user: str
    author_id: str


class ApprovalNotice(BaseModel):
    version_id: str
    reviewer_id: str
    decision: str
    recipients: list[str] = Field(default_factory=list)


VersionUploadedNotice.model_rebuild()
CommentNotice.model_rebuild()
MentionNotice.model_rebuild()
ApprovalNotice.model_rebuild()


def _assert_permission(role: Role, action: str) -> None:
    if not has_permission(role, action):
        raise HTTPException(status_code=403, detail=f"Role {role.value} cannot perform {action}")


def _create_event(request: NotificationRequest) -> NotificationEvent:
    event = NotificationEvent(
        event_id=str(uuid4()),
        event_type=request.event_type,
        recipient=request.recipient,
        subject=request.subject,
        body=request.body,
        metadata=request.metadata,
        status="queued",
    )
    notifications.append(event)
    return event


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/notify/send")
async def send_notification(request: NotificationRequest, actor_role: Role = Role.ADMIN) -> dict[str, Any]:
    _assert_permission(actor_role, "notification:send")
    return _create_event(request).model_dump(mode="json")


@app.post("/notify/version-uploaded")
async def version_uploaded(request: VersionUploadedNotice, actor_role: Role = Role.ADMIN) -> dict[str, Any]:
    _assert_permission(actor_role, "notification:send")
    recipients = request.recipients or ["project_team"]
    created: list[dict[str, Any]] = []
    for recipient in recipients:
        event = _create_event(
            NotificationRequest(
                event_type=NotificationType.VERSION_UPLOADED,
                recipient=recipient,
                subject=f"New version in project {request.project_id}",
                body=f"Version {request.version_id} was uploaded by {request.author_id}",
                metadata={"project_id": request.project_id, "version_id": request.version_id},
            )
        )
        created.append(event.model_dump(mode="json"))
    return {"items": created, "count": len(created)}


@app.post("/notify/comment")
async def comment_added(request: CommentNotice, actor_role: Role = Role.ADMIN) -> dict[str, Any]:
    _assert_permission(actor_role, "notification:send")
    recipients = request.recipients or ["project_reviewers"]
    created: list[dict[str, Any]] = []
    for recipient in recipients:
        event = _create_event(
            NotificationRequest(
                event_type=NotificationType.COMMENT_ADDED,
                recipient=recipient,
                subject=f"Comment on version {request.version_id}",
                body=f"Comment {request.comment_id} added by {request.author_id}",
                metadata={"version_id": request.version_id, "comment_id": request.comment_id},
            )
        )
        created.append(event.model_dump(mode="json"))
    return {"items": created, "count": len(created)}


@app.post("/notify/mention")
async def mentioned(request: MentionNotice, actor_role: Role = Role.ADMIN) -> dict[str, Any]:
    _assert_permission(actor_role, "notification:send")
    event = _create_event(
        NotificationRequest(
            event_type=NotificationType.USER_MENTIONED,
            recipient=request.mentioned_user,
            subject=f"You were mentioned in version {request.version_id}",
            body=f"{request.author_id} mentioned you in comment {request.comment_id}",
            metadata={"version_id": request.version_id, "comment_id": request.comment_id},
        )
    )
    return event.model_dump(mode="json")


@app.post("/notify/approval")
async def approval_changed(request: ApprovalNotice, actor_role: Role = Role.ADMIN) -> dict[str, Any]:
    _assert_permission(actor_role, "notification:send")
    recipients = request.recipients or ["project_designers"]
    created: list[dict[str, Any]] = []
    for recipient in recipients:
        event = _create_event(
            NotificationRequest(
                event_type=NotificationType.APPROVAL_CHANGED,
                recipient=recipient,
                subject=f"Approval updated for version {request.version_id}",
                body=f"{request.reviewer_id} set decision to {request.decision}",
                metadata={"version_id": request.version_id, "decision": request.decision},
            )
        )
        created.append(event.model_dump(mode="json"))
    return {"items": created, "count": len(created)}


@app.get("/notify/history")
async def history(recipient: str | None = None) -> dict[str, Any]:
    items = notifications
    if recipient is not None:
        items = [item for item in notifications if item.recipient == recipient]
    payload = [item.model_dump(mode="json") for item in items]
    return {"items": payload, "count": len(payload)}