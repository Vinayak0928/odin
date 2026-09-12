"""
chroma_client.py

Singleton ChromaDB HTTP client.
Connects to a ChromaDB instance running as a standalone service.
"""

import os
import socket
import logging

logger = logging.getLogger(__name__)

_client = None

# A short connect probe so an unreachable ChromaDB fails fast instead of
# blocking on the OS connection timeout (~30-60s, WinError 10060 on Windows),
# which otherwise stalls app startup. Tunable via CHROMADB_CONNECT_TIMEOUT.
_CONNECT_TIMEOUT = float(os.getenv("CHROMADB_CONNECT_TIMEOUT", "2.0"))


def _port_open(host: str, port: int, timeout: float = None) -> bool:
    """Return True if a TCP connection to host:port succeeds within timeout."""
    target_host = "127.0.0.1" if host in ("localhost", "127.0.0.1") else host
    try:
        with socket.create_connection((target_host, port), timeout=timeout or _CONNECT_TIMEOUT):
            return True
    except OSError:
        return False


def _try_auto_start_chroma(host: str, port: int) -> bool:
    """Attempt to auto-launch local ChromaDB service if installed."""
    if host not in ("localhost", "127.0.0.1"):
        return False

    import sys
    import subprocess
    import shutil
    import time
    from src.constants import DATA_DIR

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    chroma_data = os.path.join(DATA_DIR, "chroma")
    os.makedirs(chroma_data, exist_ok=True)

    venv_py = os.path.join(base_dir, "venv", "Scripts", "python.exe")
    if not os.path.exists(venv_py):
        venv_py = os.path.join(base_dir, "venv", "bin", "python")

    python_exe = venv_py if os.path.exists(venv_py) else sys.executable
    if not python_exe:
        logger.warning("Local Python executable not found; cannot auto-start ChromaDB")
        return False

    chroma_script = (
        f"import sys; sys.argv=['chroma', 'run', '--path', r'{chroma_data}', '--port', '{port}', '--host', '127.0.0.1']; "
        f"from chromadb.cli.cli import app; app()"
    )
    cmd = [python_exe, "-c", chroma_script]

    logger.info("Auto-starting local ChromaDB service on 127.0.0.1:%s using %s...", port, python_exe)

    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NO_WINDOW

    try:
        subprocess.Popen(
            cmd,
            creationflags=creationflags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        logger.warning("Failed to spawn ChromaDB subprocess: %s", e)
        return False

    for _ in range(20):
        time.sleep(0.25)
        if _port_open("127.0.0.1", port, timeout=0.5):
            logger.info("Local ChromaDB service successfully started and ready on 127.0.0.1:%s", port)
            return True

    return False


def get_chroma_client():
    """Get or create the singleton ChromaDB HTTP client.

    Raises RuntimeError with a clear install hint if the `chromadb` package
    is not installed — it's an optional dependency (RAG + memory vectors).
    """
    global _client
    if _client is not None:
        return _client

    try:
        import chromadb
    except ImportError as e:
        raise RuntimeError(
            "ChromaDB integration is not installed. Install the optional "
            "dependency with: pip install chromadb-client"
        ) from e

    host = os.getenv("CHROMADB_HOST", "localhost")
    port = int(os.getenv("CHROMADB_PORT", "8100"))

    if not _port_open(host, port):
        if not _try_auto_start_chroma(host, port):
            raise RuntimeError(
                f"ChromaDB is not reachable at {host}:{port}. Start the ChromaDB "
                f"service (e.g. `docker compose up chromadb` or `run-chromadb.bat`) or set CHROMADB_HOST / "
                f"CHROMADB_PORT to point at a running instance."
            )

    client = chromadb.HttpClient(host=host, port=port)

    # Health check before caching — if the port is open but the service isn't
    # healthy yet (e.g. still starting), don't poison the singleton with a dead
    # client; leave _client unset so the next call retries.
    client.heartbeat()
    _client = client
    logger.info(f"ChromaDB connected: {host}:{port}")
    return _client


def reset_client():
    """Reset the singleton (e.g. after config change)."""
    global _client
    _client = None
