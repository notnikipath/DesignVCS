# DesignVCS

DesignVCS is a microservice platform for version control of design assets (PSD, AI, Sketch, Figma, JPG/PNG, video/animation), with history, visual diff, collaboration, browser preview, export, and notifications.

## Implemented modules

- `project-service`: projects, folders, role access
- `version-service`: version upload/register, history, checksums, image/frame diff
- `collaboration-service`: comments, mentions, approval workflow
- `viewer-service`: preview generation and browser viewer state
- `export-service`: PDF export artifacts
- `notification-service`: events for upload/comment/mention/approval
- `api-gateway`: auth + orchestration workflows
- `frontend`: React + Canvas API dashboard

## Repository structure

```text
Task_22_DesignVCS/
+-- api-gateway/
+-- project-service/
+-- version-service/
+-- collaboration-service/
+-- viewer-service/
+-- export-service/
+-- notification-service/
+-- shared/
+-- frontend/
+-- docs/
+-- scripts/
L-- tests/
```

## Technology stack

- Backend: Python FastAPI
- Metadata DB target: PostgreSQL
- File storage target: MinIO
- Queue target: RabbitMQ / Celery-ready
- Cache: Redis
- Frontend: React + Canvas API

## Quick start

```bash
cd DesignVCS
docker compose up --build -d
```

Useful URLs:

- Frontend: `http://localhost:5178`
- Gateway: `http://localhost:8520`
- Swagger: `http://localhost:8520/docs`

## Local validation

```bash
python -m ruff check .
python -m pytest -q
```

## Demo workflow

```bash
python scripts/demo_workflow.py
```

## Optional improvements implemented

1. Preview caching (Group C.1)
2. Asynchronous preview conversion (Group C.4)
3. Parallel processing readiness for uploads (Group C.2)
4. Comment anchors on layout (Group D.2)
