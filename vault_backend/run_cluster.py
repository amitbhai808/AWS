#!/usr/bin/env python3
"""Vault v0.1-beta — Cluster Launcher.

Spawns N storage-node daemons, the coordinator API gateway, and monitors
for graceful shutdown on ``SIGINT`` / ``SIGTERM``.

Usage::

    python run_cluster.py
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path


def main() -> None:
    # Lazy-import so PYTHONPATH is already set when the module loads
    src_dir = str(Path(__file__).resolve().parent / "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    from vault.core.config import get_settings

    settings = get_settings()
    processes: list[subprocess.Popen] = []
    base_dir = Path(__file__).resolve().parent

    env = os.environ.copy()
    env["PYTHONPATH"] = src_dir

    print("=" * 64)
    print("   Vault v0.1-beta — Distributed Object Storage Cluster")
    print("=" * 64)

    # ── 1. Storage nodes ──────────────────────────────────────────────
    for port in settings.NODE_PORTS:
        data_dir = base_dir / "data" / f"node_{port}"
        data_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            sys.executable, "-m", "vault.daemon_main",
            "--port", str(port),
            "--data-dir", str(data_dir),
        ]
        print(f"   [LAUNCHER] Storage node  :{port}  →  {data_dir}")
        proc = subprocess.Popen(cmd, env=env)
        processes.append(proc)

    # Brief pause so nodes bind their ports before the coordinator boots
    time.sleep(1)

    # ── 2. Coordinator gateway ────────────────────────────────────────
    coord_cmd = [
        sys.executable, "-m", "uvicorn",
        "vault.coordinator_main:app",
        "--host", "0.0.0.0",
        "--port", str(settings.COORDINATOR_PORT),
        "--log-level", "info",
    ]
    print(f"   [LAUNCHER] Coordinator   :{settings.COORDINATOR_PORT}")
    coord_proc = subprocess.Popen(coord_cmd, env=env)
    processes.append(coord_proc)

    # ── Summary ───────────────────────────────────────────────────────
    print()
    print(f"   API Gateway : http://localhost:{settings.COORDINATOR_PORT}")
    print(f"   API Docs    : http://localhost:{settings.COORDINATOR_PORT}/docs")
    for port in settings.NODE_PORTS:
        print(f"   Storage Node: http://localhost:{port}")
    print()
    print("   Press Ctrl+C to shut down the cluster.")
    print("=" * 64)

    # ── 3. Graceful shutdown handler ──────────────────────────────────
    def shutdown(signum, frame):  # noqa: ARG001
        print("\n   [LAUNCHER] Shutting down cluster …")
        for proc in reversed(processes):
            try:
                proc.terminate()
            except OSError:
                pass
        for proc in processes:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        print("   [LAUNCHER] All processes terminated. Goodbye!")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # ── 4. Keep alive & watch for unexpected exits ────────────────────
    try:
        while True:
            for i, proc in enumerate(processes):
                rc = proc.poll()
                if rc is not None:
                    print(
                        f"   [LAUNCHER] ⚠ Process {i} (PID {proc.pid}) "
                        f"exited with code {rc}"
                    )
            time.sleep(2)
    except KeyboardInterrupt:
        shutdown(None, None)


if __name__ == "__main__":
    main()
