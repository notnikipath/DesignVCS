from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException

from shared.designvcs_common import (
    AccessGrantRequest,
    FolderCreateRequest,
    FolderRecord,
    ProjectCreateRequest,
    ProjectMember,
    ProjectRecord,
    Role,
    Settings,
    build_audit_event,
    has_permission,
)

settings = Settings(service_name="project-service", service_port=8421)
app = FastAPI(title="DesignVCS Project Service", version="1.0.0")

projects: dict[str, ProjectRecord] = {}
audit_log: list[dict[str, Any]] = []


def _assert_permission(role: Role, action: str) -> None:
    if not has_permission(role, action):
        raise HTTPException(status_code=403, detail=f"Role {role.value} cannot perform {action}")


def _audit(actor_id: str, actor_role: Role, action: str, object_id: str, details: dict[str, Any] | None = None) -> None:
    audit_log.append(
        build_audit_event(
            actor_id=actor_id,
            actor_role=actor_role.value,
            action=action,
            object_type="project",
            object_id=object_id,
            details=details or {},
        )
    )


def _seed_demo() -> None:
    root = FolderRecord(folder_id="FOLDER-ROOT", name="Root", path="/")
    brand = FolderRecord(folder_id="FOLDER-BRAND", name="Brand", parent_folder_id=root.folder_id, path="/Brand")
    layouts = FolderRecord(folder_id="FOLDER-LAYOUTS", name="Layouts", parent_folder_id=root.folder_id, path="/Layouts")
    project = ProjectRecord(
        project_id="PRJ-DEMO",
        name="Brand refresh kit",
        description="Demo project for DesignVCS",
        visibility="internal",
        owner_id="owner_1",
        folders=[root, brand, layouts],
        members=[
            ProjectMember(user_id="owner_1", role=Role.OWNER),
            ProjectMember(user_id="designer_1", role=Role.DESIGNER),
            ProjectMember(user_id="reviewer_1", role=Role.REVIEWER),
        ],
    )
    projects[project.project_id] = project


_seed_demo()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.get("/projects")
async def list_projects(member_id: str | None = None) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for project in projects.values():
        if member_id is not None and all(member.user_id != member_id for member in project.members):
            continue
        items.append(project.model_dump(mode="json"))
    return {"items": items, "count": len(items)}


@app.get("/projects/{project_id}")
async def get_project(project_id: str, actor_role: Role = Role.VIEWER) -> dict[str, Any]:
    _assert_permission(actor_role, "project:read")
    project = projects.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project.model_dump(mode="json")


@app.post("/projects")
async def create_project(request: ProjectCreateRequest) -> dict[str, Any]:
    project = ProjectRecord(
        project_id=str(uuid4()),
        name=request.name,
        description=request.description,
        visibility=request.visibility,
        owner_id=request.owner_id,
        folders=[FolderRecord(folder_id=str(uuid4()), name="Root", path="/")],
        members=[ProjectMember(user_id=request.owner_id, role=Role.OWNER)],
    )
    projects[project.project_id] = project
    _audit(request.owner_id, Role.OWNER, "project.create", project.project_id)
    return project.model_dump(mode="json")


@app.post("/projects/{project_id}/folders")
async def create_folder(project_id: str, request: FolderCreateRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "project:update")
    project = projects.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    base_path = "/"
    if request.parent_folder_id:
        parent = next((folder for folder in project.folders if folder.folder_id == request.parent_folder_id), None)
        if parent is None:
            raise HTTPException(status_code=404, detail="Parent folder not found")
        base_path = parent.path

    path = f"/{request.name}" if base_path == "/" else f"{base_path}/{request.name}"
    folder = FolderRecord(
        folder_id=str(uuid4()),
        name=request.name,
        parent_folder_id=request.parent_folder_id,
        path=path,
    )
    project.folders.append(folder)
    _audit(
        request.actor_id,
        request.actor_role,
        "project.folder.create",
        project_id,
        {"folder_id": folder.folder_id, "path": folder.path},
    )
    return folder.model_dump(mode="json")


@app.post("/projects/{project_id}/members")
async def grant_access(project_id: str, request: AccessGrantRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "project:access")
    project = projects.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    existing = next((member for member in project.members if member.user_id == request.user_id), None)
    if existing is not None:
        existing.role = request.role
        member = existing
        action = "project.member.update"
    else:
        member = ProjectMember(user_id=request.user_id, role=request.role)
        project.members.append(member)
        action = "project.member.add"

    _audit(
        request.actor_id,
        request.actor_role,
        action,
        project_id,
        {"user_id": request.user_id, "role": request.role.value},
    )
    return member.model_dump(mode="json")


@app.get("/projects/{project_id}/members")
async def list_members(project_id: str, actor_role: Role = Role.VIEWER) -> dict[str, Any]:
    _assert_permission(actor_role, "project:read")
    project = projects.get(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    items = [member.model_dump(mode="json") for member in project.members]
    return {"items": items, "count": len(items)}


@app.get("/audit")
async def get_audit(limit: int = 100, actor_role: Role = Role.ADMIN) -> dict[str, Any]:
    _assert_permission(actor_role, "audit:read")
    return {"items": audit_log[-limit:]}