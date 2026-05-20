from __future__ import annotations

from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from shared.designvcs_common import (
    ApprovalDecision,
    Role,
    Settings,
    UploadWorkflowRequest,
    UploadWorkflowResult,
    VersionCompareRequest,
    sign_token,
    verify_token,
)

settings = Settings(service_name="api-gateway", service_port=8420)
app = FastAPI(title="DesignVCS API Gateway", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5178", "http://127.0.0.1:5178"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AuthRequest(BaseModel):
    user_id: str
    role: Role
    language: str = Field(default="ru", pattern="^(ru|en)$")


class ReviewWorkflowRequest(BaseModel):
    version_id: str
    comment_author_id: str
    comment_body: str
    reviewer_id: str
    decision: ApprovalDecision
    notes: str = ""


class CompareProxyRequest(BaseModel):
    against_version_id: str
    mode: str = "image"


AuthRequest.model_rebuild()
ReviewWorkflowRequest.model_rebuild()
CompareProxyRequest.model_rebuild()


async def _get_json(client: httpx.AsyncClient, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = await client.get(url, params=params)
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


async def _post_json(
    client: httpx.AsyncClient,
    url: str,
    payload: dict[str, Any],
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = await client.post(url, json=payload, params=params)
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


def _service_urls() -> dict[str, str]:
    return {
        "project": settings.project_service_url,
        "version": settings.version_service_url,
        "collaboration": settings.collab_service_url,
        "viewer": settings.viewer_service_url,
        "export": settings.export_service_url,
        "notification": settings.notification_service_url,
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/auth/token")
async def issue_token(request: AuthRequest) -> dict[str, str]:
    token = sign_token(
        {"sub": request.user_id, "role": request.role.value, "language": request.language},
        settings.jwt_secret,
        exp_minutes=settings.token_exp_minutes,
    )
    return {"access_token": token, "token_type": "Bearer"}


@app.post("/auth/verify")
async def verify_auth(token: str) -> dict[str, Any]:
    payload = verify_token(token, settings.jwt_secret)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload


@app.get("/services/health")
async def service_health() -> dict[str, Any]:
    statuses: dict[str, Any] = {}
    async with httpx.AsyncClient(timeout=10.0) as client:
        for name, base_url in _service_urls().items():
            try:
                statuses[name] = await _get_json(client, f"{base_url}/health")
            except Exception as exc:
                statuses[name] = {"status": "error", "detail": str(exc)}
    return statuses


@app.post("/workflow/upload-version")
async def upload_version_workflow(request: UploadWorkflowRequest, wait_for_preview: bool = False) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20.0) as client:
        version = await _post_json(
            client,
            f"{settings.version_service_url}/versions/register",
            {
                "project_id": request.project_id,
                "folder_id": request.folder_id,
                "file_name": request.file_name,
                "file_format": request.file_format.value,
                "size_bytes": request.size_bytes,
                "author_id": request.author_id,
                "change_note": request.change_note,
            },
            params={"actor_role": Role.DESIGNER.value, "async_preview": str(not wait_for_preview).lower()},
        )

        members = await _get_json(
            client,
            f"{settings.project_service_url}/projects/{request.project_id}/members",
            params={"actor_role": Role.VIEWER.value},
        )
        recipients = [item["user_id"] for item in members.get("items", [])]
        notifications = await _post_json(
            client,
            f"{settings.notification_service_url}/notify/version-uploaded",
            {
                "project_id": request.project_id,
                "version_id": version["version_id"],
                "author_id": request.author_id,
                "recipients": recipients,
            },
            params={"actor_role": Role.ADMIN.value},
        )

        preview: dict[str, Any] = {"status": "scheduled"}
        if wait_for_preview:
            preview = await _post_json(
                client,
                f"{settings.viewer_service_url}/viewer/preview/generate",
                {
                    "version_id": version["version_id"],
                    "project_id": request.project_id,
                    "file_format": request.file_format.value,
                    "file_key": version["file_key"],
                },
            )

    result = UploadWorkflowResult(version=version, preview=preview, notifications=notifications.get("items", []))
    return result.model_dump(mode="json")


@app.post("/workflow/review-round")
async def review_round(request: ReviewWorkflowRequest) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20.0) as client:
        comment = await _post_json(
            client,
            f"{settings.collab_service_url}/versions/{request.version_id}/comments",
            {
                "author_id": request.comment_author_id,
                "body": request.comment_body,
                "mentions": [],
            },
            params={"actor_role": Role.DESIGNER.value},
        )
        approval = await _post_json(
            client,
            f"{settings.collab_service_url}/versions/{request.version_id}/approvals",
            {
                "reviewer_id": request.reviewer_id,
                "decision": request.decision.value,
                "notes": request.notes,
            },
            params={"actor_role": Role.REVIEWER.value},
        )
    return {"comment": comment, "approval": approval}


@app.get("/projects/{project_id}/versions")
async def project_versions(project_id: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        return await _get_json(
            client,
            f"{settings.version_service_url}/versions/project/{project_id}",
            params={"actor_role": Role.VIEWER.value},
        )


@app.get("/projects/{project_id}/members")
async def project_members(project_id: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        return await _get_json(
            client,
            f"{settings.project_service_url}/projects/{project_id}/members",
            params={"actor_role": Role.VIEWER.value},
        )


@app.get("/versions/{version_id}/preview")
async def version_preview(version_id: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        return await _get_json(client, f"{settings.viewer_service_url}/viewer/preview/{version_id}")


@app.post("/versions/{version_id}/compare")
async def compare_versions_proxy(version_id: str, request: CompareProxyRequest) -> dict[str, Any]:
    compare_request = VersionCompareRequest(
        against_version_id=request.against_version_id,
        mode=request.mode,
    )
    async with httpx.AsyncClient(timeout=20.0) as client:
        return await _post_json(
            client,
            f"{settings.version_service_url}/versions/{version_id}/compare",
            compare_request.model_dump(mode="json"),
            params={"actor_role": Role.REVIEWER.value},
        )
