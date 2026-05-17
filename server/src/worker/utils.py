import logging
import signal
from pathlib import Path

from src.config import settings

logger = logging.getLogger("AnalyticsWorker.Utils")

# Global State for Graceful Shutdown
SHUTDOWN_REQUESTED = False

def setup_signal_handlers():
    """Set up signal handlers for graceful shutdown."""
    def handle_shutdown(sig, frame):
        global SHUTDOWN_REQUESTED
        if not SHUTDOWN_REQUESTED:
            logger.info(f"Shutdown signal {sig} received. Finishing current batch...")
            SHUTDOWN_REQUESTED = True
    
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

def is_shutdown_requested() -> bool:
    """Check if a shutdown has been requested."""
    global SHUTDOWN_REQUESTED
    return SHUTDOWN_REQUESTED

def touch_healthcheck_file():
    """Signals that the worker is alive and processing."""
    try:
        Path(settings.WORKER_HEALTHCHECK_FILE_PATH).touch()
    except Exception as e:
        logger.warning(f"Could not touch healthcheck file: {e}")
