from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from shared.designvcs_common import (
    AssetFormat,
    Settings,
    TTLCache,
    ViewerActionRequest,
    ViewerSessionState,
    build_preview_key,
)

settings = Settings(service_name="viewer-service", service_port=8424)
app = FastAPI(title="DesignVCS Viewer Service", version="1.0.0")

preview_cache: TTLCache[dict[str, Any]] = TTLCache(ttl_seconds=180)
previews: dict[str, dict[str, Any]] = {}
viewer_sessions: dict[str, ViewerSessionState] = {}


class PreviewGenerateRequest(BaseModel):
    version_id: str
    project_id: str
    file_format: AssetFormat
    file_key: str
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)
    duration_seconds: float | None = Field(default=None, ge=0)


PreviewGenerateRequest.model_rebuild()


def _storage_root() -> Path:
    local_root = Path(__file__).resolve().parents[3] / "data" / "minio"
    if local_root.exists() or local_root.parent.exists():
        local_root.mkdir(parents=True, exist_ok=True)
        return local_root
    tmp_root = Path("/tmp/designvcs-minio")
    tmp_root.mkdir(parents=True, exist_ok=True)
    return tmp_root


def _create_preview_file(preview_key: str, request: PreviewGenerateRequest) -> str:
    root = _storage_root()
    target = root / preview_key
    target.parent.mkdir(parents=True, exist_ok=True)
    content = (
        f"preview for {request.version_id}\n"
        f"format={request.file_format.value}\n"
        f"file={request.file_key}\n"
        f"size={request.width or '-'}x{request.height or '-'}\n"
        f"duration={request.duration_seconds or 0}\n"
    )
    target.write_text(content, encoding="utf-8")
    return str(target)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/viewer/preview/generate")
async def generate_preview(request: PreviewGenerateRequest) -> dict[str, Any]:
    cached = preview_cache.get(request.version_id)
    if cached is not None:
        return {**cached, "cached": True}

    started = datetime.now(UTC)
    preview_key = build_preview_key(request.project_id, request.version_id, request.file_format)
    file_path = _create_preview_file(preview_key, request)
    duration_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)

    payload = {
        "version_id": request.version_id,
        "preview_key": preview_key,
        "preview_path": file_path,
        "generated_at": datetime.now(UTC).isoformat(),
        "generation_ms": duration_ms,
        "cached": False,
    }
    previews[request.version_id] = payload
    preview_cache.set(request.version_id, payload)
    return payload


@app.get("/viewer/preview/{version_id}")
async def get_preview(version_id: str) -> dict[str, Any]:
    payload = preview_cache.get(version_id)
    if payload is not None:
        return {**payload, "cached": True}

    payload = previews.get(version_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Preview not found")
    preview_cache.set(version_id, payload)
    return {**payload, "cached": False}


@app.post("/viewer/actions")
async def set_viewer_state(request: ViewerActionRequest) -> dict[str, Any]:
    state = ViewerSessionState(
        version_id=request.version_id,
        zoom=request.zoom,
        rotation_deg=request.rotation_deg,
        slide_index=request.slide_index,
        transforms={"scale": request.zoom, "rotation": float(request.rotation_deg)},
    )
    viewer_sessions[request.version_id] = state
    return state.model_dump(mode="json")


@app.get("/viewer/actions/{version_id}")
async def get_viewer_state(version_id: str) -> dict[str, Any]:
    state = viewer_sessions.get(version_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Viewer state not found")
    return state.model_dump(mode="json")


@app.get("/viewer/slideshow")
async def slideshow(version_ids: str) -> dict[str, Any]:
    ids = [value.strip() for value in version_ids.split(",") if value.strip()]
    items: list[dict[str, Any]] = []
    for version_id in ids:
        preview = previews.get(version_id)
        if preview is None:
            continue
        items.append({"version_id": version_id, "preview_key": preview["preview_key"]})
    return {"items": items, "count": len(items)}


@app.get("/viewer/cache/stats")
async def cache_stats() -> dict[str, int]:
    return {"preview_cache_size": preview_cache.size(), "preview_total": len(previews)}