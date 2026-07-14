import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.routes import router

# Each open SSE connection holds one worker thread (blocked on q.get() via
# asyncio.to_thread) for the duration of a research run -- asyncio's default
# executor (~min(32, cpu_count+4) workers) would silently cap concurrent visitors
# well below MAX_CONCURRENT_RESEARCH in api/stream.py, so it's upsized explicitly.
THREAD_POOL_SIZE = 64

DEV_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    loop = asyncio.get_running_loop()
    loop.set_default_executor(ThreadPoolExecutor(max_workers=THREAD_POOL_SIZE))
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Research Agent API", lifespan=_lifespan)

    app.add_middleware(
        CORSMiddleware,
        # Same-origin in production (FastAPI serves the built SPA itself), so this
        # only matters for local dev where Vite runs on a different port.
        allow_origins=DEV_ORIGINS,
        allow_methods=["POST"],
        allow_headers=["*"],
    )

    # Registered before the static mount below so /api/* is never shadowed by it.
    app.include_router(router, prefix="/api")

    dist = Path(__file__).resolve().parent.parent / "web" / "dist"
    if dist.exists():
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")

    return app


app = create_app()
