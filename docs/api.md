# API Reference

## API Gateway

- `GET /health`
- `GET /services/health`
- `POST /auth/token`
- `POST /auth/verify`
- `POST /workflow/upload-version`
- `POST /workflow/review-round`
- `GET /projects/{project_id}/versions`
- `GET /versions/{version_id}/preview`
- `POST /versions/{version_id}/compare`

## Project Service

- `GET /health`
- `GET /projects`
- `GET /projects/{project_id}`
- `POST /projects`
- `POST /projects/{project_id}/folders`
- `POST /projects/{project_id}/members`
- `GET /projects/{project_id}/members`

## Version Service

- `GET /health`
- `POST /versions/register`
- `POST /versions/upload` (JSON + optional `content_base64`)
- `GET /versions/project/{project_id}`
- `GET /versions/{version_id}`
- `GET /versions/{version_id}/download-info`
- `GET /versions/{version_id}/content`
- `POST /versions/{version_id}/compare`
- `GET /metrics`

## Collaboration Service

- `GET /health`
- `POST /versions/{version_id}/comments`
- `GET /versions/{version_id}/comments`
- `POST /versions/{version_id}/approvals`
- `GET /versions/{version_id}/approvals`

## Viewer Service

- `GET /health`
- `POST /viewer/preview/generate`
- `GET /viewer/preview/{version_id}`
- `POST /viewer/actions`
- `GET /viewer/actions/{version_id}`
- `GET /viewer/slideshow`

## Export Service

- `GET /health`
- `POST /exports/pdf`
- `GET /exports/{artifact_id}`
- `GET /exports/version/{version_id}`

## Notification Service

- `GET /health`
- `POST /notify/send`
- `POST /notify/version-uploaded`
- `POST /notify/comment`
- `POST /notify/mention`
- `POST /notify/approval`
- `GET /notify/history`
