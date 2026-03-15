from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .routers import areas, projects, tasks, notes, files, extension, llm, config, backup


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="FlowTrack API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(areas.router)
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(notes.router)
app.include_router(files.router)
app.include_router(extension.router)
app.include_router(llm.router)
app.include_router(config.router)
app.include_router(backup.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
