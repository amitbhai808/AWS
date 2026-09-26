"""Entry point for Storage Node Daemon.

Launch with::

    python -m vault.daemon_main --port 8001 --data-dir ./data/node_8001

Or via uvicorn directly (uses default port/data-dir)::

    uvicorn vault.daemon_main:app --port 8001
"""

from __future__ import annotations

import argparse

import uvicorn
from fastapi import FastAPI

from vault.api.storage.router import configure, router as storage_router


def create_app(data_dir: str = "./data", port: int = 8001) -> FastAPI:
    """Build a configured storage-node FastAPI application."""
    application = FastAPI(
        title=f"Vault Storage Node (:{port})",
        version="0.1.0-beta",
    )
    configure(data_dir=data_dir, port=port)
    application.include_router(storage_router)
    return application


def main() -> None:
    """CLI entry point with ``--port`` and ``--data-dir`` arguments."""
    parser = argparse.ArgumentParser(description="Vault Storage Node Daemon")
    parser.add_argument(
        "--port",
        type=int,
        default=8001,
        help="Port to listen on (default: 8001)",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="./data",
        help="Directory for chunk storage (default: ./data)",
    )
    args = parser.parse_args()

    application = create_app(data_dir=args.data_dir, port=args.port)
    uvicorn.run(application, host="0.0.0.0", port=args.port, log_level="info")


# Default app instance for ``uvicorn vault.daemon_main:app`` usage
app = create_app()

if __name__ == "__main__":
    main()
