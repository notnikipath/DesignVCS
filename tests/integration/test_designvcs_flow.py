from pathlib import Path

from fastapi.testclient import TestClient

from tests.integration.helpers import load_module

ROOT = Path(__file__).resolve().parents[2]

project_module = load_module("project_module", ROOT / "project-service" / "app" / "main.py")
version_module = load_module("version_module", ROOT / "version-service" / "app" / "main.py")
viewer_module = load_module("viewer_module", ROOT / "viewer-service" / "app" / "main.py")
collab_module = load_module("collab_module", ROOT / "collaboration-service" / "app" / "main.py")

project_client = TestClient(project_module.app)
version_client = TestClient(version_module.app)
viewer_client = TestClient(viewer_module.app)
collab_client = TestClient(collab_module.app)


async def _fake_dispatch(version):
    version.preview_key = f"previews/{version.project_id}/{version.version_id}.png"
    version.processing_ms = 3


def test_project_members_and_folder_creation() -> None:
    members = project_client.get("/projects/PRJ-DEMO/members", params={"actor_role": "viewer"})
    assert members.status_code == 200
    assert members.json()["count"] >= 3

    folder = project_client.post(
        "/projects/PRJ-DEMO/folders",
        json={
            "name": "Screens",
            "parent_folder_id": "FOLDER-LAYOUTS",
            "actor_id": "owner_1",
            "actor_role": "owner",
        },
    )
    assert folder.status_code == 200
    assert folder.json()["path"].endswith("/Screens")


def test_version_diff_and_collaboration(monkeypatch) -> None:
    monkeypatch.setattr(version_module, "_dispatch_preview_and_notifications", _fake_dispatch)

    first = version_client.post(
        "/versions/register?async_preview=false",
        json={
            "project_id": "PRJ-DEMO",
            "folder_id": "FOLDER-LAYOUTS",
            "file_name": "home_v3.psd",
            "file_format": "psd",
            "size_bytes": 440000,
            "author_id": "designer_1",
            "change_note": "Refined hero",
        },
    )
    assert first.status_code == 200
    first_version = first.json()

    second = version_client.post(
        "/versions/register?async_preview=false",
        json={
            "project_id": "PRJ-DEMO",
            "folder_id": "FOLDER-LAYOUTS",
            "file_name": "home_v4.psd",
            "file_format": "psd",
            "size_bytes": 480000,
            "author_id": "designer_1",
            "change_note": "Changed CTA",
        },
    )
    assert second.status_code == 200
    second_version = second.json()

    compare = version_client.post(
        f"/versions/{second_version['version_id']}/compare",
        params={"actor_role": "reviewer"},
        json={"against_version_id": first_version["version_id"], "mode": "image"},
    )
    assert compare.status_code == 200
    assert compare.json()["similarity_score"] <= 100

    comment = collab_client.post(
        f"/versions/{second_version['version_id']}/comments",
        params={"actor_role": "designer"},
        json={
            "author_id": "designer_1",
            "body": "Please review @reviewer_1",
            "mentions": [],
        },
    )
    assert comment.status_code == 200
    assert "reviewer_1" in comment.json()["mentions"]

    approval = collab_client.post(
        f"/versions/{second_version['version_id']}/approvals",
        params={"actor_role": "reviewer"},
        json={
            "reviewer_id": "reviewer_1",
            "decision": "approved",
            "notes": "Looks good",
        },
    )
    assert approval.status_code == 200
    assert approval.json()["summary"]["status"] == "approved"

    preview = viewer_client.post(
        "/viewer/preview/generate",
        json={
            "version_id": second_version["version_id"],
            "project_id": "PRJ-DEMO",
            "file_format": "psd",
            "file_key": second_version["file_key"],
        },
    )
    assert preview.status_code == 200
    assert preview.json()["preview_key"].startswith("previews/PRJ-DEMO/")