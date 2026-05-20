# Deployment

## Local prerequisites

- Docker Desktop
- Python 3.11+ (for lint/test outside containers)

## Run stack

```bash
docker compose up --build -d
```

## Stop stack

```bash
docker compose down
```

## Main URLs

- Gateway: `http://localhost:8520`
- Gateway docs: `http://localhost:8520/docs`
- Frontend: `http://localhost:5178`
- MinIO console: `http://localhost:19001`
- RabbitMQ console: `http://localhost:15673`

## Validation

```bash
python -m ruff check .
python -m pytest -q
docker compose config
```

## Demo script

```bash
python scripts/demo_workflow.py
```