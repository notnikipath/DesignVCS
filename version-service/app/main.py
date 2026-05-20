from __future__ import annotations

import asyncio
import base64
import hashlib
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from shared.designvcs_common import (
    AssetFormat,
    DiffMode,
    Role,
    Settings,
    VersionCompareRequest,
    VersionRecord,
    VersionRegisterRequest,
    VersionStatus,
    compare_versions,
    has_permission,
)

settings = Settings(service_name="version-service", service_port=8422)
app = FastAPI(title="DesignVCS Version Service", version="1.0.0")

versions: dict[str, VersionRecord] = {}
versions_by_project: dict[str, list[str]] = {}
compare_results: dict[str, dict[str, Any]] = {}
metrics: dict[str, list[int]] = {"upload_ms": [], "preview_ms": []}


class UploadBinaryRequest(BaseModel):
    project_id: str
    author_id: str
    file_format: AssetFormat
    file_name: str
    size_bytes: int
    folder_id: str | None = None
    change_note: str = ""
    actor_role: Role = Role.DESIGNER
    async_preview: bool = True
    content_base64: str | None = None


def _assert_permission(role: Role, action: str) -> None:
    if not has_permission(role, action):
        raise HTTPException(status_code=403, detail=f"Role {role.value} cannot perform {action}")


def _storage_root() -> Path:
    resolved = Path(__file__).resolve()
    local_root = resolved.parents[1] / "data" / "minio"
    if local_root.exists() or local_root.parent.exists():
        local_root.mkdir(parents=True, exist_ok=True)
        return local_root
    tmp_root = Path("/tmp/designvcs-minio")
    tmp_root.mkdir(parents=True, exist_ok=True)
    return tmp_root


def _sanitize_filename(file_name: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]", "_", file_name)
    return value[:180] if value else "asset.bin"


def _next_sequence(project_id: str) -> int:
    return len(versions_by_project.get(project_id, [])) + 1


def _save_bytes(project_id: str, version_id: str, file_name: str, data: bytes) -> str:
    safe_name = _sanitize_filename(file_name)
    file_key = f"assets/{project_id}/{version_id}_{safe_name}"
    path = _storage_root() / file_key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return file_key


def _checksum_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _version_from_request(
    request: VersionRegisterRequest,
    file_key: str,
    checksum: str,
    sequence_number: int,
    upload_ms: int,
) -> VersionRecord:
    return VersionRecord(
        version_id=str(uuid4()),
        project_id=request.project_id,
        folder_id=request.folder_id,
        sequence_number=sequence_number,
        file_name=request.file_name,
        file_format=request.file_format,
        size_bytes=request.size_bytes,
        author_id=request.author_id,
        change_note=request.change_note,
        file_key=file_key,
        checksum_sha256=checksum,
        status=VersionStatus.READY,
        upload_ms=upload_ms,
    )


async def _dispatch_preview_and_notifications(version: VersionRecord) -> None:
    async with httpx.AsyncClient(timeout=12.0) as client:
        try:
            preview_response = await client.post(
                f"{settings.viewer_service_url}/viewer/preview/generate",
                json={
                    "version_id": version.version_id,
                    "project_id": version.project_id,
                    "file_format": version.file_format.value,
                    "file_key": version.file_key,
                },
            )
            if preview_response.status_code < 400:
                payload = preview_response.json()
                version.preview_key = payload.get("preview_key")
                version.processing_ms = payload.get("generation_ms")
                if version.processing_ms is not None:
                    metrics["preview_ms"].append(int(version.processing_ms))
        except httpx.HTTPError:
            pass

        try:
            await client.post(
                f"{settings.notification_service_url}/notify/version-uploaded",
                json={
                    "project_id": version.project_id,
                    "version_id": version.version_id,
                    "author_id": version.author_id,
                    "recipients": ["project_team"],
                },
                params={"actor_role": Role.ADMIN.value},
            )
        except httpx.HTTPError:
            pass


def _store_version(version: VersionRecord) -> None:
    versions[version.version_id] = version
    versions_by_project.setdefault(version.project_id, []).append(version.version_id)


def _seed_demo() -> None:
    demo_content = b"Demo design binary content"
    demo_request = VersionRegisterRequest(
        project_id="PRJ-DEMO",
        folder_id="FOLDER-LAYOUTS",
        file_name="landing_mockup.psd",
        file_format=AssetFormat.PSD,
        size_bytes=len(demo_content),
        author_id="designer_1",
        change_note="Initial concept",
    )
    version_id = "VER-DEMO-1"
    file_key = _save_bytes(demo_request.project_id, version_id, demo_request.file_name, demo_content)
    version = VersionRecord(
        version_id=version_id,
        project_id=demo_request.project_id,
        folder_id=demo_request.folder_id,
        sequence_number=1,
        file_name=demo_request.file_name,
        file_format=demo_request.file_format,
        size_bytes=demo_request.size_bytes,
        author_id=demo_request.author_id,
        change_note=demo_request.change_note,
        file_key=file_key,
        checksum_sha256=_checksum_sha256(demo_content),
        status=VersionStatus.READY,
        upload_ms=2,
        processing_ms=4,
        preview_key=f"previews/{demo_request.project_id}/{version_id}.png",
    )
    _store_version(version)


_seed_demo()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/versions/register")
async def register_version(
    request: VersionRegisterRequest,
    actor_role: Role = Role.DESIGNER,
    async_preview: bool = True,
) -> dict[str, Any]:
    _assert_permission(actor_role, "version:upload")
    if request.size_bytes > settings.max_file_size_bytes:
        raise HTTPException(status_code=413, detail="File too large")

    sequence_number = _next_sequence(request.project_id)
    synthetic_payload = (
        f"{request.project_id}:{request.file_name}:{request.author_id}:{request.size_bytes}:{datetime.now(UTC).isoformat()}"
    ).encode()
    checksum = _checksum_sha256(synthetic_payload)
    version_id = str(uuid4())
    file_key = _save_bytes(request.project_id, version_id, request.file_name, synthetic_payload)

    version = VersionRecord(
        version_id=version_id,
        project_id=request.project_id,
        folder_id=request.folder_id,
        sequence_number=sequence_number,
        file_name=request.file_name,
        file_format=request.file_format,
        size_bytes=request.size_bytes,
        author_id=request.author_id,
        change_note=request.change_note,
        file_key=file_key,
        checksum_sha256=checksum,
        status=VersionStatus.READY,
        upload_ms=10,
    )
    _store_version(version)
    metrics["upload_ms"].append(version.upload_ms or 0)

    if async_preview:
        asyncio.create_task(_dispatch_preview_and_notifications(version))
    else:
        await _dispatch_preview_and_notifications(version)

    return version.model_dump(mode="json")


@app.post("/versions/upload")
async def upload_version(request: UploadBinaryRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "version:upload")
    if request.size_bytes > settings.max_file_size_bytes:
        raise HTTPException(status_code=413, detail="File too large")

    started = datetime.now(UTC)
    if request.content_base64:
        content = base64.b64decode(request.content_base64.encode("ascii"))
    else:
        content = (
            f"{request.project_id}:{request.file_name}:{request.author_id}:{datetime.now(UTC).isoformat()}"
        ).encode()
    real_size = len(content)
    if real_size > settings.max_file_size_bytes:
        raise HTTPException(status_code=413, detail="File too large")

    sequence_number = _next_sequence(request.project_id)
    version_id = str(uuid4())
    file_key = _save_bytes(request.project_id, version_id, request.file_name, content)
    checksum = _checksum_sha256(content)
    upload_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)

    version = VersionRecord(
        version_id=version_id,
        project_id=request.project_id,
        folder_id=request.folder_id,
        sequence_number=sequence_number,
        file_name=request.file_name,
        file_format=request.file_format,
        size_bytes=real_size,
        author_id=request.author_id,
        change_note=request.change_note,
        file_key=file_key,
        checksum_sha256=checksum,
        status=VersionStatus.READY,
        upload_ms=upload_ms,
    )
    _store_version(version)
    metrics["upload_ms"].append(upload_ms)

    if request.async_preview:
        asyncio.create_task(_dispatch_preview_and_notifications(version))
    else:
        await _dispatch_preview_and_notifications(version)

    return version.model_dump(mode="json")


@app.get("/versions/project/{project_id}")
async def list_versions(project_id: str, actor_role: Role = Role.VIEWER) -> dict[str, Any]:
    _assert_permission(actor_role, "version:read")
    ids = versions_by_project.get(project_id, [])
    items = [versions[version_id].model_dump(mode="json") for version_id in ids]
    items.sort(key=lambda item: item["sequence_number"]) 
    return {"items": items, "count": len(items)}


@app.get("/versions/{version_id}")
async def get_version(version_id: str, actor_role: Role = Role.VIEWER) -> dict[str, Any]:
    _assert_permission(actor_role, "version:read")
    version = versions.get(version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Version not found")
    return version.model_dump(mode="json")


@app.get("/versions/{version_id}/download-info")
async def download_info(version_id: str, actor_role: Role = Role.VIEWER) -> dict[str, Any]:
    _assert_permission(actor_role, "version:read")
    version = versions.get(version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Version not found")

    full_path = _storage_root() / version.file_key
    return {
        "version_id": version.version_id,
        "file_name": version.file_name,
        "file_key": version.file_key,
        "file_path": str(full_path),
        "exists": full_path.exists(),
        "size_bytes": version.size_bytes,
    }


@app.get("/versions/{version_id}/content")
async def get_version_content(
    version_id: str,
    max_bytes: int = 262_144,
    actor_role: Role = Role.VIEWER,
) -> dict[str, Any]:
    _assert_permission(actor_role, "version:read")
    version = versions.get(version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Version not found")

    full_path = _storage_root() / version.file_key
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="Binary file not found")

    raw = full_path.read_bytes()
    clipped = raw[:max_bytes]
    encoded = base64.b64encode(clipped).decode("ascii")
    return {
        "version_id": version.version_id,
        "content_base64": encoded,
        "truncated": len(raw) > len(clipped),
        "returned_bytes": len(clipped),
    }


@app.post("/versions/{version_id}/compare")
async def compare(version_id: str, request: VersionCompareRequest, actor_role: Role = Role.REVIEWER) -> dict[str, Any]:
    _assert_permission(actor_role, "version:compare")
    base = versions.get(version_id)
    target = versions.get(request.against_version_id)
    if base is None or target is None:
        raise HTTPException(status_code=404, detail="One of versions not found")

    result = compare_versions(
        base_version_id=base.version_id,
        target_version_id=target.version_id,
        base_checksum=base.checksum_sha256,
        target_checksum=target.checksum_sha256,
        base_size=base.size_bytes,
        target_size=target.size_bytes,
        mode=request.mode,
    )
    key = f"{base.version_id}:{target.version_id}:{request.mode.value}"
    compare_results[key] = result.model_dump(mode="json")
    return result.model_dump(mode="json")


@app.get("/versions/{version_id}/compare/{against_version_id}")
async def get_compare_result(
    version_id: str,
    against_version_id: str,
    mode: DiffMode = DiffMode.IMAGE,
) -> dict[str, Any]:
    key = f"{version_id}:{against_version_id}:{mode.value}"
    result = compare_results.get(key)
    if result is None:
        raise HTTPException(status_code=404, detail="Comparison not found")
    return result


@app.get("/metrics")
async def service_metrics() -> dict[str, Any]:
    upload_samples = metrics["upload_ms"]
    preview_samples = metrics["preview_ms"]
    avg_upload = round(sum(upload_samples) / len(upload_samples), 2) if upload_samples else 0
    avg_preview = round(sum(preview_samples) / len(preview_samples), 2) if preview_samples else 0
    return {
        "versions_total": len(versions),
        "upload_count": len(upload_samples),
        "preview_count": len(preview_samples),
        "avg_upload_ms": avg_upload,
        "avg_preview_ms": avg_preview,
        "upload_slo_seconds": settings.upload_slo_seconds,
        "preview_slo_seconds": settings.preview_slo_seconds,
    }
