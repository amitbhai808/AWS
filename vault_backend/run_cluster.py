import os
import signal
import subprocess
import sys
import time

def kill_ports(ports):
    """Clean up any old processes clinging to cluster ports."""
    for port in ports:
        try:
            out = subprocess.check_output(["lsof", "-t", f"-i:{port}"], text=True).strip()
            if out:
                for pid_str in out.split():
                    pid = int(pid_str)
                    if pid != os.getpid():
                        print(f"Cleaning up stale process {pid} on port {port}...")
                        os.kill(pid, signal.SIGKILL)
        except Exception:
            pass

def main():
    cluster_ports = [8000, 8001, 8002, 8003, 8004]
    kill_ports(cluster_ports)
    time.sleep(0.5)

    procs = []

    def shutdown(signum=None, frame=None):
        print("\nShutting down cluster processes...")
        for p in procs:
            if p.poll() is None:
                p.terminate()
        for p in procs:
            try:
                p.wait(timeout=2)
            except Exception:
                p.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # 1. Start storage nodes
    for i in range(1, 5):
        port = 8000 + i
        data_dir = f"./data/node{i}"
        os.makedirs(data_dir, exist_ok=True)
        p = subprocess.Popen([
            sys.executable, "-m", "vault.daemon_main",
            "--port", str(port),
            "--data-dir", data_dir
        ])
        procs.append(p)

    time.sleep(0.5)

    # 2. Start coordinator
    p_coord = subprocess.Popen([
        sys.executable, "-m", "uvicorn",
        "vault.coordinator_main:app",
        "--port", "8000"
    ])
    procs.append(p_coord)

    print("\n✅ Vault Cluster running successfully!")
    print(" - Coordinator: http://localhost:8000")
    print(" - Storage Nodes: http://localhost:8001 - 8004")
    print("Press Ctrl+C to stop.\n")

    try:
        while True:
            for p in procs:
                if p.poll() is not None:
                    # One process exited prematurely
                    print(f"Process {p.args} exited with code {p.returncode}")
                    shutdown()
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown()

if __name__ == "__main__":
    main()
