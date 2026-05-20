from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field


class Role(str, Enum):
    OWNER = "owner"
    DESIGNER = "designer"
    REVIEWER = "reviewer"
    VIEWER = "viewer"
    ADMIN = "admin"


class ProjectVisibility(str, Enum):
    PRIVATE = "private"
    INTERNAL = "internal"
    PUBLIC = "public"


class AssetFormat(str, Enum):
    PSD = "psd"
    AI = "ai"
    SKETCH = "sketch"
    FIGMA = "figma"
    JPG = "jpg"
    PNG = "png"
    MP4 = "mp4"
    MOV = "mov"
    GIF = "gif"
    WEBM = "webm"


class VersionStatus(str, Enum):
    UPLOADING = "uploading"
    READY = "ready"
    FAILED = "failed"


class DiffMode(str, Enum):
    IMAGE = "image"
    FRAME = "frame"


class ApprovalDecision(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    REJECTED = "rejected"


class NotificationType(str, Enum):
    VERSION_UPLOADED = "version_uploaded"
    COMMENT_ADDED = "comment_added"
    USER_MENTIONED = "user_mentioned"
    APPROVAL_CHANGED = "approval_changed"


class FolderRecord(BaseModel):
    folder_id: str
    name: str
    parent_folder_id: str | None = None
    path: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ProjectMember(BaseModel):
    user_id: str
    role: Role
    added_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    description: str = Field(default="", max_length=500)
    owner_id: str
    visibility: ProjectVisibility = ProjectVisibility.PRIVATE


class ProjectRecord(BaseModel):
    project_id: str
    name: str
    description: str
    visibility: ProjectVisibility
    owner_id: str
    folders: list[FolderRecord] = Field(default_factory=list)
    members: list[ProjectMember] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class FolderCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    parent_folder_id: str | None = None
    actor_id: str
    actor_role: Role


class AccessGrantRequest(BaseModel):
    user_id: str
    role: Role
    actor_id: str
    actor_role: Role


class VersionRegisterRequest(BaseModel):
    project_id: str
    folder_id: str | None = None
    file_name: str
    file_format: AssetFormat
    size_bytes: int = Field(gt=0)
    author_id: str
    change_note: str = Field(default="", max_length=2000)
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)
    duration_seconds: float | None = Field(default=None, ge=0)


class VersionRecord(BaseModel):
    version_id: str
    project_id: str
    folder_id: str | None
    sequence_number: int = Field(ge=1)
    file_name: str
    file_format: AssetFormat
    size_bytes: int = Field(gt=0)
    author_id: str
    change_note: str
    file_key: str
    checksum_sha256: str
    status: VersionStatus
    preview_key: str | None = None
    upload_ms: int | None = None
    processing_ms: int | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class VersionCompareRequest(BaseModel):
    against_version_id: str
    mode: DiffMode = DiffMode.IMAGE


class VersionDiffResult(BaseModel):
    base_version_id: str
    target_version_id: str
    mode: DiffMode
    pixel_delta_pct: float = Field(ge=0, le=100)
    changed_frames: int = Field(ge=0)
    similarity_score: float = Field(ge=0, le=100)
    summary: str


class CommentCreateRequest(BaseModel):
    author_id: str
    body: str = Field(min_length=1, max_length=2000)
    mentions: list[str] = Field(default_factory=list)
    anchor_x: float | None = Field(default=None, ge=0, le=1)
    anchor_y: float | None = Field(default=None, ge=0, le=1)


class CommentRecord(BaseModel):
    comment_id: str
    version_id: str
    author_id: str
    body: str
    mentions: list[str] = Field(default_factory=list)
    anchor_x: float | None = None
    anchor_y: float | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ApprovalRequest(BaseModel):
    reviewer_id: str
    decision: ApprovalDecision
    notes: str = Field(default="", max_length=2000)


class ApprovalRecord(BaseModel):
    approval_id: str
    version_id: str
    reviewer_id: str
    decision: ApprovalDecision
    notes: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class NotificationRequest(BaseModel):
    event_type: NotificationType
    recipient: str
    subject: str
    body: str
    metadata: dict[str, str] = Field(default_factory=dict)


class NotificationEvent(BaseModel):
    event_id: str
    event_type: NotificationType
    recipient: str
    subject: str
    body: str
    metadata: dict[str, str]
    status: str = "queued"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ExportPdfRequest(BaseModel):
    version_id: str
    author_id: str
    include_comments: bool = True


class ExportArtifact(BaseModel):
    artifact_id: str
    version_id: str
    output_format: str
    download_name: str
    content_base64: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ViewerActionRequest(BaseModel):
    version_id: str
    zoom: float = Field(default=1.0, ge=0.1, le=8.0)
    rotation_deg: int = Field(default=0, ge=-180, le=180)
    slide_index: int = Field(default=0, ge=0)


class ViewerSessionState(BaseModel):
    version_id: str
    zoom: float
    rotation_deg: int
    slide_index: int
    transforms: dict[str, float] = Field(default_factory=dict)


class UploadWorkflowRequest(BaseModel):
    project_id: str
    folder_id: str | None = None
    file_name: str
    file_format: AssetFormat
    size_bytes: int = Field(gt=0)
    author_id: str
    change_note: str = Field(default="", max_length=2000)


class UploadWorkflowResult(BaseModel):
    version: dict
    preview: dict
    notifications: list[dict]