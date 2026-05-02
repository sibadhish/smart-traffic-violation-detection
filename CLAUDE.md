# Smart Traffic Violation Detection System

## Project overview
AI-powered traffic enforcement platform that detects violations from camera feeds, recognizes license plates, and generates evidence packages.

## Architecture
- **Backend**: FastAPI + Celery (Python 3.12) in `backend/`
- **Frontend**: React 19 + Vite + TypeScript + Tailwind in `frontend/`
- **ML Pipeline**: YOLOv8 detection -> ByteTrack tracking -> PaddleOCR plate reading in `backend/app/services/`
- **Infrastructure**: PostgreSQL, Redis via Docker Compose; local filesystem or MinIO for media

## Quick start (local dev)

```bash
# 1. Start dev dependencies
docker compose -f docker-compose.dev.yml up -d

# 2. Backend
cd backend
pip install -r requirements.txt
cp .env .env  # or edit as needed
alembic upgrade head
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

# 3. Celery worker (separate terminal)
cd backend
celery -A backend.app.workers.celery_app worker --loglevel=info

# 4. Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## Commands
- Backend: `cd backend && uvicorn backend.app.main:app --reload`
- Celery worker: `cd backend && celery -A backend.app.workers.celery_app worker --loglevel=info`
- Frontend: `cd frontend && npm run dev`
- Docker (dev deps only): `docker compose -f docker-compose.dev.yml up -d`
- Docker (all services): `docker compose up`
- DB migrations: `cd backend && alembic upgrade head`
- Tests: `cd backend && pytest`
- Tests with coverage: `cd backend && pytest --cov=backend`

## Key paths
- API routes: `backend/app/api/routes/` (violations, cameras, processing)
- ML services: `backend/app/services/detection/`, `ocr/`, `tracking/`, `violations/`
- Processing pipeline: `backend/app/services/pipeline.py`
- Video ingest: `backend/app/services/video_ingest.py`
- Clip extractor: `backend/app/services/clip_extractor.py`
- Config: `backend/app/core/config.py`
- Storage abstraction: `backend/app/core/storage.py`
- Models/schemas: `backend/app/models/`, `backend/app/schemas/`
- Celery tasks: `backend/app/workers/tasks.py`
- PDF reports: `backend/app/services/violations/pdf_report.py`
- Tests: `backend/tests/`

## Frontend pages
- Dashboard: `/` — stats cards + violation charts
- Violations: `/violations` — filterable table with plate search
- Violation Detail: `/violations/:id` — video player, annotated frame, actions
- Upload: `/upload` — drag-and-drop video upload with processing progress
- Cameras: `/cameras` — add/remove cameras, start stream processing

## API endpoints
- `GET /health` — health check
- `GET /api/v1/violations/` — list violations (filters: camera_id, type, status, date range)
- `GET /api/v1/violations/stats` — violation statistics
- `GET /api/v1/violations/{id}` — single violation detail
- `PATCH /api/v1/violations/{id}` — update status/plate
- `GET /api/v1/violations/{id}/evidence` — download evidence ZIP bundle
- `GET /api/v1/cameras/` — list cameras
- `POST /api/v1/cameras/` — register camera
- `DELETE /api/v1/cameras/{id}` — delete camera
- `POST /api/v1/process/upload` — upload video for processing
- `POST /api/v1/process/stream` — start stream processing
- `GET /api/v1/process/status/{task_id}` — check processing task status

## Conventions
- Python imports use full `backend.app.*` paths
- API versioned under `/api/v1`
- Frontend proxies `/api` to backend via Vite config
- Storage mode defaults to `local` (filesystem); set `STORAGE_MODE=minio` for S3-compatible storage
- Violation confirmation requires MIN_VIOLATION_FRAMES consecutive detections (default: 5)
- YOLOv8n auto-downloads if not present in `ml/models/`
