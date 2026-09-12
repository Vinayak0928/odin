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
    try:
        with socket.create_connection((host, port), timeout=timeout or _CONNECT_TIMEOUT):
            return True
    except OSError:
        return False


def _try_auto_start_chroma(host: str, port: int) -> bool:
    """Attempt to auto-launch local ChromaDB service if installed."""
    if host not in ("localhost", "127.0.0.1"):
        return False

    import subprocess
    import shutil
    import time
    from src.constants import DATA_DIR

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = [
        os.path.join(base_dir, "venv", "Scripts", "chroma.exe"),
        os.path.join(base_dir, "venv", "bin", "chroma"),
        shutil.which("chroma.exe"),
        shutil.which("chroma"),
    ]
    chroma_exe = next((c for c in candidates if c and os.path.exists(c)), None)
    if not chroma_exe:
        logger.warning("Local chroma executable not found; cannot auto-start ChromaDB")
        return False

    chroma_data = os.path.join(DATA_DIR, "chroma")
    os.makedirs(chroma_data, exist_ok=True)
    logger.info("Auto-starting local ChromaDB service on %s:%s using %s...", host, port, chroma_exe)

    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NO_WINDOW

    try:
        subprocess.Popen(
            [chroma_exe, "run", "--path", chroma_data, "--port", str(port)],
            creationflags=creationflags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        logger.warning("Failed to spawn ChromaDB subprocess: %s", e)
        return False

    for _ in range(16):
        time.sleep(0.5)
        if _port_open(host, port, timeout=0.8):
            logger.info("Local ChromaDB service successfully started and ready on %s:%s", host, port)
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
