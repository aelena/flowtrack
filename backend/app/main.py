import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .database import init_db
from .routers import (
    areas,
    backup,
    config,
    documents,
    extension,
    files,
    metrics,
    notes,
    projects,
    tasks,
)

logger = logging.getLogger("flowtrack")

PROBLEM_JSON = "application/problem+json"

HTTP_STATUS_PHRASES = {
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    409: "Conflict",
    413: "Content Too Large",
    422: "Unprocessable Content",
    500: "Internal Server Error",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="FlowTrack API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "type": "about:blank",
            "title": HTTP_STATUS_PHRASES.get(exc.status_code, "Error"),
            "status": exc.status_code,
            "detail": exc.detail,
        },
        media_type=PROBLEM_JSON,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    first = errors[0] if errors else {}
    field = " -> ".join(str(part) for part in first.get("loc", [])) if first else "unknown"
    msg = first.get("msg", "Validation error")
    return JSONResponse(
        status_code=422,
        content={
            "type": "about:blank",
            "title": "Unprocessable Content",
            "status": 422,
            "detail": f"{field}: {msg}",
            "errors": [
                {
                    "field": " -> ".join(str(part) for part in e.get("loc", [])),
                    "message": e.get("msg", ""),
                }
                for e in errors
            ],
        },
        media_type=PROBLEM_JSON,
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "type": "about:blank",
            "title": "Internal Server Error",
            "status": 500,
            "detail": "An unexpected error occurred",
        },
        media_type=PROBLEM_JSON,
    )


app.include_router(areas.router)
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(notes.router)
app.include_router(files.router)
app.include_router(extension.router)
app.include_router(documents.router)
app.include_router(config.router)
app.include_router(backup.router)
app.include_router(metrics.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
