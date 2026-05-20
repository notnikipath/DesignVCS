# Architecture

## Goal

DesignVCS is a Git-like version control platform for design assets: PSD, AI, Sketch, Figma, raster images, and video/animation files.

## Service map

- `api-gateway`: unified entrypoint, auth tokens, workflow orchestration, health aggregation.
- `project-service`: projects, folder tree, access control and role assignment.
- `version-service`: version upload/register, history, file checksums, visual/frame diff.
- `collaboration-service`: threaded comments, mentions, approval workflow.
- `viewer-service`: browser preview metadata, conversion records, zoom/rotation/slideshow state.
- `export-service`: PDF export artifact generation.
- `notification-service`: new version, mentions, comments, approval notifications.
- `frontend`: React dashboard with Canvas-based preview panel.

## Infrastructure

- `PostgreSQL`: metadata storage target (project, versions, comments) for production mode.
- `MinIO`: binary objects (source files and previews).
- `RabbitMQ`: async task transport target for preview and notification workers.
- `Redis`: preview cache and short-lived viewer state acceleration.

Local implementation in this assignment uses in-memory repositories plus file-backed storage under `data/minio` to keep setup lightweight.

## Core flow: upload version

1. Client sends upload request to `api-gateway`.
2. `version-service` creates version record and file object key.
3. Preview generation is started asynchronously (`viewer-service`).
4. Project members receive notifications (`notification-service`).
5. Version appears in history and can be compared with previous versions.

## Scalability notes

- Preview cache (`viewer-service`) reduces repeated generation.
- Async preview dispatch avoids blocking upload response path.
- Services are independent and can be horizontally scaled by traffic profile.
- `version-service` records upload/preview timings to monitor SLO targets.