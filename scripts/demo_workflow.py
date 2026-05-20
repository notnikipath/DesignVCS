from __future__ import annotations

import json

import httpx


async def run_demo() -> None:
    async with httpx.AsyncClient(base_url="http://localhost:8520", timeout=20.0) as client:
        health = await client.get("/services/health")
        print("Health:", json.dumps(health.json(), indent=2))

        upload = await client.post(
            "/workflow/upload-version",
            params={"wait_for_preview": "true"},
            json={
                "project_id": "PRJ-DEMO",
                "folder_id": "FOLDER-LAYOUTS",
                "file_name": "landing_homepage_v5.psd",
                "file_format": "psd",
                "size_bytes": 650000,
                "author_id": "designer_1",
                "change_note": "Adjusted promo section and footer",
            },
        )
        upload.raise_for_status()
        payload = upload.json()
        print("Upload:", json.dumps(payload, indent=2))

        review = await client.post(
            "/workflow/review-round",
            json={
                "version_id": payload["version"]["version_id"],
                "comment_author_id": "designer_1",
                "comment_body": "Please check spacing and typography @reviewer_1",
                "reviewer_id": "reviewer_1",
                "decision": "approved",
                "notes": "Approved after spacing fixes",
            },
        )
        review.raise_for_status()
        print("Review:", json.dumps(review.json(), indent=2))


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_demo())