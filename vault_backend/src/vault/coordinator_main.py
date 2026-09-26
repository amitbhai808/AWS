"""Entry point for Central API Gateway (uvicorn).

Launch with::

    uvicorn vault.coordinator_main:app --port 8000

The lifespan context manager initialises the database schema and starts the
background repair worker on startup, then tears both down on shutdown.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from vault.api.coordinator.router import router as coordinator_router
from vault.core.config import get_settings
from vault.core.database import init_db
from vault.workers.repair_worker import RepairWorker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("vault.coordinator")

settings = get_settings()
_repair_worker = RepairWorker()


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Startup / shutdown lifecycle hook."""
    # ── Startup ───────────────────────────────────────────────────────
    logger.info("Initialising database tables …")
    await init_db()

    logger.info("Launching background repair worker …")
    worker_task = asyncio.create_task(_repair_worker.run())

    yield

    # ── Shutdown ──────────────────────────────────────────────────────
    logger.info("Stopping repair worker …")
    _repair_worker.stop()
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass
    logger.info("Coordinator shut down cleanly.")


from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Vault Coordinator API",
    description=(
        "Central API Gateway for Vault v0.1-beta — "
        "fault-tolerant distributed object storage"
    ),
    version="0.1.0-beta",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(coordinator_router)

