from __future__ import annotations

import base64
from typing import Any
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException

from shared.designvcs_common import ExportArtifact, ExportPdfRequest, Role, Settings, has_permission, make_pdf_payload

settings = Settings(service_name="export-service", service_port=8425)
app = FastAPI(title="DesignVCS Export Service", version="1.0.0")

exports: dict[str, ExportArtifact] = {}


def _assert_permission(role: Role, action: str) -> None:
    if not has_permission(role, action):
        raise HTTPException(status_code=403, detail=f"Role {role.value} cannot perform {action}")


async def _get_json(client: httpx.AsyncClient, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = await client.get(url, params=params)
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/exports/pdf")
async def export_pdf(request: ExportPdfRequest, actor_role: Role = Role.REVIEWER) -> dict[str, Any]:
    _assert_permission(actor_role, "export:pdf")

    async with httpx.AsyncClient(timeout=20.0) as client:
        version = await _get_json(
            client,
            f"{settings.version_service_url}/versions/{request.version_id}",
            params={"actor_role": Role.VIEWER.value},
        )

        comments_count = 0
        approval_summary: dict[str, Any] = {"status": "pending"}
        if request.include_comments:
            comments = await _get_json(
                client,
                f"{settings.collab_service_url}/versions/{request.version_id}/comments",
            )
            approvals = await _get_json(
                client,
                f"{settings.collab_service_url}/versions/{request.version_id}/approvals",
            )
            comments_count = comments["count"]
            approval_summary = approvals.get("summary", {"status": "pending"})

    text = make_pdf_payload(request.version_id, version["file_name"], comments_count, approval_summary)
    encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")

    artifact = ExportArtifact(
        artifact_id=str(uuid4()),
        version_id=request.version_id,
        output_format="pdf",
        download_name=f"{version['file_name']}.pdf",
        content_base64=encoded,
    )
    exports[artifact.artifact_id] = artifact
    return artifact.model_dump(mode="json")


@app.get("/exports/{artifact_id}")
async def get_export(artifact_id: str, actor_role: Role = Role.VIEWER) -> dict[str, Any]:
    _assert_permission(actor_role, "version:read")
    artifact = exports.get(artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Export artifact not found")
    return artifact.model_dump(mode="json")


@app.get("/exports/version/{version_id}")
async def list_exports(version_id: str) -> dict[str, Any]:
    items = [item.model_dump(mode="json") for item in exports.values() if item.version_id == version_id]
    return {"items": items, "count": len(items)}
