from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.api.routes import cameras, violations, processing
from backend.app.core.config import settings
from backend.app.core.storage import ensure_buckets


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create storage dirs / MinIO buckets on startup
    ensure_buckets()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(violations.router, prefix="/api/v1")
app.include_router(cameras.router, prefix="/api/v1")
app.include_router(processing.router, prefix="/api/v1")

# Serve locally stored clips/thumbnails/evidence as static files
if settings.STORAGE_MODE == "local":
    import os
    for name, path in [
        ("clips", settings.CLIPS_DIR),
        ("thumbnails", settings.THUMBNAILS_DIR),
        ("evidence", settings.EVIDENCE_DIR),
    ]:
        os.makedirs(path, exist_ok=True)
        app.mount(f"/static/{name}", StaticFiles(directory=path), name=name)


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.APP_NAME}
