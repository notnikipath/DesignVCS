from __future__ import annotations

import hashlib
import re
from typing import Any

from .schemas import AssetFormat, DiffMode, VersionDiffResult

VIDEO_FORMATS = {AssetFormat.MP4, AssetFormat.MOV, AssetFormat.WEBM, AssetFormat.GIF}


def is_video_format(file_format: AssetFormat) -> bool:
    return file_format in VIDEO_FORMATS


def build_preview_key(project_id: str, version_id: str, file_format: AssetFormat) -> str:
    suffix = "jpg" if is_video_format(file_format) else "png"
    return f"previews/{project_id}/{version_id}.{suffix}"


def detect_mentions(text: str) -> list[str]:
    matches = re.findall(r"@([A-Za-z0-9_.-]{2,64})", text)
    unique: list[str] = []
    for match in matches:
        if match not in unique:
            unique.append(match)
    return unique


def estimate_frame_changes(base_size: int, target_size: int) -> int:
    gap = abs(target_size - base_size)
    if gap == 0:
        return 0
    return max(1, min(900, gap // 40_000))


def compare_versions(
    base_version_id: str,
    target_version_id: str,
    base_checksum: str,
    target_checksum: str,
    base_size: int,
    target_size: int,
    mode: DiffMode,
) -> VersionDiffResult:
    source = f"{base_checksum}:{target_checksum}:{mode.value}"
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()

    distance = sum(1 for idx in range(len(base_checksum)) if base_checksum[idx] != target_checksum[idx])
    size_factor = min(100.0, abs(target_size - base_size) / max(base_size, 1) * 100)
    pixel_delta = round(min(100.0, distance * 1.3 + size_factor * 0.4), 2)

    similarity = round(max(0.0, 100.0 - pixel_delta * 0.9), 2)
    changed_frames = estimate_frame_changes(base_size, target_size) if mode == DiffMode.FRAME else 0

    summary = (
        f"Diff hash {digest[:10]}: delta={pixel_delta}% similarity={similarity}% "
        f"frames_changed={changed_frames}"
    )
    return VersionDiffResult(
        base_version_id=base_version_id,
        target_version_id=target_version_id,
        mode=mode,
        pixel_delta_pct=pixel_delta,
        changed_frames=changed_frames,
        similarity_score=similarity,
        summary=summary,
    )


def make_pdf_payload(version_id: str, version_title: str, comment_count: int, approvals: dict[str, Any]) -> str:
    content = (
        f"DesignVCS export\n"
        f"version={version_id}\n"
        f"title={version_title}\n"
        f"comments={comment_count}\n"
        f"approvals={approvals}\n"
    )
    return content